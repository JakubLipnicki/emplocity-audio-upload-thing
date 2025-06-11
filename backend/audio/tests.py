import uuid
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import AudioFile, Tag, Like

User = get_user_model()


# FINALNA, OSTATECZNA POPRAWKA:
# 1. @patch('storages.backends.s3.S3Storage._save', ...):
#    Patchujemy metodę _save w BAZOWEJ klasie S3Storage. To jest właściwy cel.
#    Zastępujemy ją funkcją lambda, która natychmiast zwraca nazwę pliku,
#    całkowicie blokując jakąkolwiek próbę połączenia z S3.
# 2. @patch('audio.models.boto3.client'):
#    Nadal potrzebne, aby odizolować sygnał `post_save`, który używa `boto3.client`.
@patch('storages.backends.s3.S3Storage._save', lambda self, name, content: name)
@patch('audio.models.boto3.client')
class AudioAPITestCase(APITestCase):
    """
    Zestaw testów dla endpointów API aplikacji 'audio'.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Metoda uruchamiana raz na początku. Tworzymy tu dane testowe.
        """
        cls.user_one = User.objects.create_user(
            email='userone@example.com', password='testpassword123', name='User One'
        )
        cls.user_two = User.objects.create_user(
            email='usertwo@example.com', password='testpassword123', name='User Two'
        )
        cls.audio_file_content = b'fake audio content'
        cls.audio_file = SimpleUploadedFile("test_track.mp3", cls.audio_file_content, content_type="audio/mpeg")
        cls.invalid_file = SimpleUploadedFile("test.txt", b"not audio", content_type="text/plain")
        cls.tag_rock = Tag.objects.create(name='rock')
        cls.tag_pop = Tag.objects.create(name='pop')

        # Teraz operacja create na pewno się powiedzie, bo _save jest zmockowane.
        cls.public_audio = AudioFile.objects.create(
            user=cls.user_one, title="Public Rock Song", file=cls.audio_file, is_public=True
        )
        cls.public_audio.tags.add(cls.tag_rock)
        cls.private_audio = AudioFile.objects.create(
            user=cls.user_one, title="Private Pop Song", file=cls.audio_file, is_public=False
        )
        cls.private_audio.tags.add(cls.tag_pop)
        cls.other_user_audio = AudioFile.objects.create(
            user=cls.user_two, title="Other User's Song", file=cls.audio_file, is_public=True
        )

        Like.objects.create(user=cls.user_one, audio_file=cls.public_audio, is_liked=True)
        Like.objects.create(user=cls.user_two, audio_file=cls.public_audio, is_liked=True)
        Like.objects.create(user=cls.user_one, audio_file=cls.other_user_audio, is_liked=False)

        cls.upload_url = reverse('audio:audio-upload')
        cls.latest_url = reverse('audio:audio-latest')
        cls.top_rated_url = reverse('audio:audio-top-rated')
        cls.tags_url = reverse('audio:tag-list')
        cls.liked_url = reverse('audio:user-liked-audio')
        cls.detail_url = reverse('audio:audio-detail', kwargs={'uuid': cls.public_audio.uuid})
        cls.delete_url = reverse('audio:audio-delete', kwargs={'uuid': cls.public_audio.uuid})
        cls.like_url = reverse('audio:audio-like', kwargs={'uuid': cls.public_audio.uuid})
        cls.likes_count_url = reverse('audio:audio-likes-count', kwargs={'uuid': cls.public_audio.uuid})

    def setUp(self):
        self.client.force_authenticate(user=self.user_one)
        self.audio_file.seek(0)
        self.invalid_file.seek(0)

    # Metody testowe przyjmują teraz tylko JEDEN argument `mock_boto_client`,
    # ponieważ pierwszy patch z funkcją lambda nie wstrzykuje argumentu.
    def test_s3_metadata_signal_called_on_create(self, mock_boto_client):
        mock_s3_instance = MagicMock()
        mock_boto_client.return_value = mock_s3_instance
        AudioFile.objects.create(user=self.user_one, title="Signal Test", file=self.audio_file)
        self.assertTrue(mock_boto_client.called)
        mock_s3_instance.copy_object.assert_called_once()

    def test_upload_audio_authenticated(self, mock_boto_client):
        data = {
            'title': 'New Uploaded Track', 'file': self.audio_file,
            'is_public': 'true', 'tags': ['new-tag', 'another-tag']
        }
        response = self.client.post(self.upload_url, data=data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AudioFile.objects.count(), 4)

    def test_upload_audio_anonymous(self, mock_boto_client):
        self.client.logout()
        data = {'title': 'Anonymous Upload', 'file': self.audio_file}
        response = self.client.post(self.upload_url, data=data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_invalid_file_type(self, mock_boto_client):
        data = {'title': 'Invalid File', 'file': self.invalid_file}
        response = self.client.post(self.upload_url, data=data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_audio_detail_and_view_increment(self, mock_boto_client):
        initial_views = self.public_audio.views
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.public_audio.refresh_from_db()
        self.assertEqual(self.public_audio.views, initial_views + 1)

    def test_get_private_audio_by_other_user(self, mock_boto_client):
        private_url = reverse('audio:audio-detail', kwargs={'uuid': self.private_audio.uuid})
        self.client.force_authenticate(user=self.user_two)
        response = self.client.get(private_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_audio_by_owner(self, mock_boto_client):
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AudioFile.objects.filter(uuid=self.public_audio.uuid).exists())

    def test_delete_audio_by_other_user(self, mock_boto_client):
        self.client.force_authenticate(user=self.user_two)
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_like(self, mock_boto_client):
        like_url = reverse('audio:audio-like', kwargs={'uuid': self.other_user_audio.uuid})
        response = self.client.post(like_url, data={'is_liked': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_dislike_to_like(self, mock_boto_client):
        like_url = reverse('audio:audio-like', kwargs={'uuid': self.other_user_audio.uuid})
        self.client.post(like_url, data={'is_liked': False})  # Set to dislike first
        response = self.client.post(like_url, data={'is_liked': True})  # Then change to like
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_likes_count(self, mock_boto_client):
        response = self.client.get(self.likes_count_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['likes'], 2)

    def test_get_user_liked_files(self, mock_boto_client):
        response = self.client.get(self.liked_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_top_rated_files(self, mock_boto_client):
        response = self.client.get(self.top_rated_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)