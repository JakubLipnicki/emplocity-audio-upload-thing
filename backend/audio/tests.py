import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AudioFile, Like, Tag

User = get_user_model()


@patch("storages.backends.s3.S3Storage._save", lambda self, name, content: name)
@patch("audio.models.boto3.client")
class AudioAPITestCase(APITestCase):
    """
    Zestaw testów dla endpointów API aplikacji 'audio'.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user_one = User.objects.create_user(
            email="userone@example.com", password="testpassword123", name="User One"
        )
        cls.user_two = User.objects.create_user(
            email="usertwo@example.com", password="testpassword123", name="User Two"
        )
        cls.audio_file_content = b"fake audio content"
        cls.audio_file = SimpleUploadedFile(
            "test_track.mp3", cls.audio_file_content, content_type="audio/mpeg"
        )
        cls.invalid_file = SimpleUploadedFile(
            "test.txt", b"not audio", content_type="text/plain"
        )
        cls.tag_rock = Tag.objects.create(name="rock")
        cls.tag_pop = Tag.objects.create(name="pop")

        cls.public_audio = AudioFile.objects.create(
            user=cls.user_one,
            title="Public Rock Song",
            file=cls.audio_file,
            is_public=True,
        )
        cls.public_audio.tags.add(cls.tag_rock)
        cls.private_audio = AudioFile.objects.create(
            user=cls.user_one,
            title="Private Pop Song",
            file=cls.audio_file,
            is_public=False,
        )
        cls.private_audio.tags.add(cls.tag_pop)
        cls.other_user_audio = AudioFile.objects.create(
            user=cls.user_two,
            title="Other User's Song",
            file=cls.audio_file,
            is_public=True,
        )

        Like.objects.create(
            user=cls.user_one, audio_file=cls.public_audio, is_liked=True
        )
        Like.objects.create(
            user=cls.user_two, audio_file=cls.public_audio, is_liked=True
        )
        Like.objects.create(
            user=cls.user_one, audio_file=cls.other_user_audio, is_liked=False
        )

        cls.upload_url = reverse("audio:audio-upload")
        cls.latest_url = reverse("audio:audio-latest")
        cls.top_rated_url = reverse("audio:audio-top-rated")
        cls.tags_url = reverse("audio:tag-list")
        cls.liked_url = reverse("audio:user-liked-audio")
        cls.detail_url = reverse(
            "audio:audio-detail", kwargs={"uuid": cls.public_audio.uuid}
        )
        cls.delete_url = reverse(
            "audio:audio-delete", kwargs={"uuid": cls.public_audio.uuid}
        )
        cls.like_url = reverse(
            "audio:audio-like", kwargs={"uuid": cls.public_audio.uuid}
        )
        cls.likes_count_url = reverse(
            "audio:audio-likes-count", kwargs={"uuid": cls.public_audio.uuid}
        )
        cls.audio_by_tag_url = reverse(
            "audio:audio-by-tag", kwargs={"tag_name": "rock"}
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user_one)
        self.audio_file.seek(0)
        self.invalid_file.seek(0)

    # --- Testy podstawowe (1-14) ---
    def test_s3_metadata_signal_called_on_create(self, mock_boto_client):
        mock_s3_instance = MagicMock()
        mock_boto_client.return_value = mock_s3_instance
        AudioFile.objects.create(
            user=self.user_one, title="Signal Test", file=self.audio_file
        )
        self.assertTrue(mock_boto_client.called)
        mock_s3_instance.copy_object.assert_called_once()

    def test_upload_audio_authenticated(self, mock_boto_client):
        data = {
            "title": "New Uploaded Track",
            "file": self.audio_file,
            "is_public": "true",
            "tags": ["new-tag", "another-tag"],
        }
        response = self.client.post(self.upload_url, data=data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_audio_anonymous(self, mock_boto_client):
        self.client.logout()
        data = {"title": "Anonymous Upload", "file": self.audio_file}
        response = self.client.post(self.upload_url, data=data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_invalid_file_type(self, mock_boto_client):
        data = {"title": "Invalid File", "file": self.invalid_file}
        response = self.client.post(self.upload_url, data=data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_audio_detail_and_view_increment(self, mock_boto_client):
        initial_views = self.public_audio.views
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.public_audio.refresh_from_db()
        self.assertEqual(self.public_audio.views, initial_views + 1)

    def test_get_private_audio_by_other_user(self, mock_boto_client):
        private_url = reverse(
            "audio:audio-detail", kwargs={"uuid": self.private_audio.uuid}
        )
        self.client.force_authenticate(user=self.user_two)
        response = self.client.get(private_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_audio_by_owner(self, mock_boto_client):
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_audio_by_other_user(self, mock_boto_client):
        self.client.force_authenticate(user=self.user_two)
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_like(self, mock_boto_client):
        like_url = reverse(
            "audio:audio-like", kwargs={"uuid": self.other_user_audio.uuid}
        )
        response = self.client.post(like_url, data={"is_liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_dislike_to_like(self, mock_boto_client):
        like_url = reverse(
            "audio:audio-like", kwargs={"uuid": self.other_user_audio.uuid}
        )
        self.client.post(like_url, data={"is_liked": False}, format="json")
        response = self.client.post(like_url, data={"is_liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_likes_count(self, mock_boto_client):
        response = self.client.get(self.likes_count_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["likes"], 2)

    def test_get_user_liked_files(self, mock_boto_client):
        response = self.client.get(self.liked_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_top_rated_files(self, mock_boto_client):
        response = self.client.get(self.top_rated_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tag_list_and_serializer_audio_count(self, mock_boto_client):
        response = self.client.get(self.tags_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        rock_tag_data = next(
            (tag for tag in response.data if tag["name"] == "rock"), None
        )
        self.assertIsNotNone(rock_tag_data)
        self.assertEqual(rock_tag_data["audio_count"], 1)

    # --- Testy widoków (15-18) ---
    def test_get_own_audio_list_authenticated(self, mock_boto_client):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_latest_audio_files_with_pagination(self, mock_boto_client):
        for i in range(11):
            AudioFile.objects.create(
                user=self.user_two,
                title=f"Latest file {i}",
                file=self.audio_file,
                is_public=True,
            )
        response = self.client.get(self.latest_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertTrue(response.data["has_more"])
        response = self.client.get(self.latest_url, {"page": 2})
        self.assertEqual(len(response.data["results"]), 3)
        self.assertFalse(response.data["has_more"])

    def test_get_top_rated_files_with_search_query(self, mock_boto_client):
        response = self.client.get(self.top_rated_url, {"search": "Public Rock"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.top_rated_url, {"search": "non-existent-song"})
        self.assertEqual(len(response.data), 0)

    def test_get_audio_files_by_tag(self, mock_boto_client):
        response = self.client.get(self.audio_by_tag_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    # --- Testy przypadków brzegowych (19-24) ---
    def test_get_public_audio_list_anonymous(self, mock_boto_client):
        self.client.logout()
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_audio_detail_anonymous(self, mock_boto_client):
        self.client.logout()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.public_audio.title)

    def test_add_like_non_existent_audio(self, mock_boto_client):
        non_existent_uuid = uuid.uuid4()
        like_url = reverse("audio:audio-like", kwargs={"uuid": non_existent_uuid})
        response = self.client.post(like_url, data={"is_liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_like_missing_is_liked_field(self, mock_boto_client):
        like_url = reverse("audio:audio-like", kwargs={"uuid": self.public_audio.uuid})
        response = self.client.post(like_url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_liked", response.data)

    def test_add_like_invalid_is_liked_field(self, mock_boto_client):
        like_url = reverse("audio:audio-like", kwargs={"uuid": self.public_audio.uuid})
        response = self.client.post(
            like_url, data={"is_liked": "not a boolean"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_liked", response.data)

    def test_get_likes_count_non_existent_audio(self, mock_boto_client):
        non_existent_uuid = uuid.uuid4()
        likes_count_url = reverse(
            "audio:audio-likes-count", kwargs={"uuid": non_existent_uuid}
        )
        response = self.client.get(likes_count_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Testy modeli (25-26) ---
    def test_model_str_methods(self, mock_boto_client):
        """Testuje metody __str__ wszystkich modeli w aplikacji audio."""
        self.assertEqual(str(self.tag_rock), "rock")
        self.assertEqual(str(self.public_audio), "Public Rock Song")
        like_instance = Like.objects.get(
            user=self.user_one, audio_file=self.public_audio
        )
        expected_str = f"{self.user_one.email} - {self.public_audio.title} - {'Like' if like_instance.is_liked else 'Dislike'}"
        self.assertEqual(str(like_instance), expected_str)

    def test_s3_metadata_signal_exceptions(self, mock_boto_client):
        """Testuje ścieżki błędów w sygnale ustawiającym metadane S3."""
        # Scenariusz 1: Błąd przy pobieraniu metadanych (head_object)
        mock_s3_instance = MagicMock()
        mock_s3_instance.head_object.side_effect = Exception(
            "Simulated S3 head_object error"
        )
        mock_boto_client.return_value = mock_s3_instance

        AudioFile.objects.create(
            user=self.user_one, title="Signal Head Fail", file=self.audio_file
        )
        mock_s3_instance.copy_object.assert_called_once()

        # Scenariusz 2: Błąd przy kopiowaniu obiektu (copy_object)
        mock_boto_client.reset_mock()
        mock_s3_instance = MagicMock()
        mock_s3_instance.head_object.return_value = {"ContentType": "audio/mpeg"}
        mock_s3_instance.copy_object.side_effect = Exception(
            "Simulated S3 copy_object error"
        )
        mock_boto_client.return_value = mock_s3_instance

        AudioFile.objects.create(
            user=self.user_one, title="Signal Copy Fail", file=self.audio_file
        )
        self.assertTrue(AudioFile.objects.filter(title="Signal Copy Fail").exists())
