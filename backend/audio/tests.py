import json
import os
import time
import uuid
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.db.models import signals
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import (
    AudioFile,
    Like,
    Tag,
    audio_file_upload_to,
    set_s3_content_disposition_metadata,
    validate_audio_file_extension,
)

try:
    from value_object import ALLOWED_AUDIO_EXTENSIONS
except ImportError:
    ALLOWED_AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg"]

User = get_user_model()


def create_dummy_file(
        filename="dummy_test_file.mp3", content=b"dummy content", content_type="audio/mpeg"
):
    return SimpleUploadedFile(name=filename, content=content, content_type=content_type)


class ModelUnitTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="modeltest@example.com", password="pw")

    def test_validate_audio_file_extension_valid(self):
        for ext in ALLOWED_AUDIO_EXTENSIONS:
            mock_file = MagicMock()
            mock_file.name = f"testfile{ext}"
            try:
                validate_audio_file_extension(mock_file)
            except ValidationError:
                self.fail(f"validate_audio_file_extension raised ValidationError unexpectedly for {ext}")

    def test_validate_audio_file_extension_invalid(self):
        mock_file = MagicMock()
        mock_file.name = "testfile.txt"
        with self.assertRaises(ValidationError):
            validate_audio_file_extension(mock_file)

    def test_audio_file_upload_to(self):
        mock_instance = MagicMock()
        mock_instance.uuid = uuid.uuid4()
        filename = "my_song.MP3"
        expected_path = f"{mock_instance.uuid}.mp3"
        self.assertEqual(audio_file_upload_to(mock_instance, filename), expected_path)

    def test_tag_str_method(self):
        tag = Tag(name="Test Tag")
        self.assertEqual(str(tag), "Test Tag")

    def test_audiofile_str_method(self):
        audio = AudioFile(title="Test Title")
        self.assertEqual(str(audio), "Test Title")

    def test_like_str_method(self):
        with patch("audio.models.set_s3_content_disposition_metadata"):
            audio = AudioFile.objects.create(title="AudioForLike", file=create_dummy_file())
        like = Like(user=self.user, audio_file=audio, is_liked=True)
        self.assertEqual(str(like), f"{self.user.email} - AudioForLike - Like")
        dislike = Like(user=self.user, audio_file=audio, is_liked=False)
        self.assertEqual(str(dislike), f"{self.user.email} - AudioForLike - Dislike")

    def test_like_unique_together_constraint(self):
        with patch("audio.models.set_s3_content_disposition_metadata"):
            audio = AudioFile.objects.create(title="UniqueAudio", file=create_dummy_file())
        Like.objects.create(user=self.user, audio_file=audio, is_liked=True)
        with self.assertRaises(IntegrityError):
            Like.objects.create(user=self.user, audio_file=audio, is_liked=False)


@patch("audio.models.boto3.client")
class AudioSignalTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="signaluser@example.com", password="password")

    def test_signal_sets_metadata_on_create(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_object.return_value = {"ContentType": "audio/mpeg"}
        with signals.post_save.disconnect_receiver(set_s3_content_disposition_metadata, sender=AudioFile):
            audio_file = AudioFile.objects.create(
                user=self.user, title="My Signal Test Song", file=create_dummy_file("signal_test.mp3"),
                s3_metadata_set=False
            )
            set_s3_content_disposition_metadata(sender=AudioFile, instance=audio_file, created=True)
        mock_boto_client.assert_called_once()
        mock_s3.copy_object.assert_called_once()
        audio_file.refresh_from_db()
        self.assertTrue(audio_file.s3_metadata_set)

    def test_signal_is_skipped_if_flag_is_true(self, mock_boto_client):
        mock_instance = MagicMock(spec=AudioFile, file=MagicMock(name="file.mp3"), s3_metadata_set=True)
        set_s3_content_disposition_metadata(sender=AudioFile, instance=mock_instance, created=False)
        mock_boto_client.assert_not_called()

    @patch('builtins.print')
    def test_signal_handles_boto_exception_gracefully(self, mock_print, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_object.return_value = {"ContentType": "audio/mpeg"}
        mock_s3.copy_object.side_effect = Exception("S3 is down")
        with signals.post_save.disconnect_receiver(set_s3_content_disposition_metadata, sender=AudioFile):
            audio_file = AudioFile.objects.create(
                user=self.user, title="Fail Song", file=create_dummy_file("fail.mp3"), s3_metadata_set=False
            )
            set_s3_content_disposition_metadata(sender=AudioFile, instance=audio_file, created=True)
        self.assertTrue(mock_s3.copy_object.called)
        audio_file.refresh_from_db()
        self.assertFalse(audio_file.s3_metadata_set)

    @patch('builtins.print')
    def test_signal_handles_head_object_exception(self, mock_print, mock_boto_client):
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_object.side_effect = Exception("head failed")
        with signals.post_save.disconnect_receiver(set_s3_content_disposition_metadata, sender=AudioFile):
            audio_file = AudioFile.objects.create(
                user=self.user, title="Head Fail", file=create_dummy_file("headfail.mp3"), s3_metadata_set=False
            )
            set_s3_content_disposition_metadata(sender=AudioFile, instance=audio_file, created=True)
        self.assertTrue(mock_s3.head_object.called)
        self.assertTrue(mock_s3.copy_object.called)
        call_args = mock_s3.copy_object.call_args.kwargs
        self.assertEqual(call_args['ContentType'], 'application/octet-stream')


class AudioFileUploadTests(APITestCase):
    def setUp(self):
        self.upload_url = reverse("audio:audio-upload")
        self.user = User.objects.create_user(email="audiotester@example.com", password="pw", name="Audio Tester")
        self.valid_upload_data = {
            "title": "Mój Super Utwór Testowy",
            "description": "Opis.",
            "is_public": True,
            "tags": ["TestTag1", "Rock"],
        }

    @patch("audio.models.post_save")
    def test_upload_audio_success_authenticated(self, mock_post_save):
        self.client.force_login(self.user)
        form_data = self.valid_upload_data.copy()
        form_data["file"] = create_dummy_file()
        response = self.client.post(self.upload_url, form_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(AudioFile.objects.filter(title=self.valid_upload_data["title"], user=self.user).exists())
        self.assertEqual(response.data["uploader"], self.user.username)

    @patch("audio.models.post_save")
    def test_upload_audio_unauthenticated(self, mock_post_save):
        form_data = self.valid_upload_data.copy()
        form_data["file"] = create_dummy_file()
        response = self.client.post(self.upload_url, form_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(AudioFile.objects.filter(title=self.valid_upload_data["title"], user=None).exists())
        self.assertEqual(response.data["uploader"], "Anonim")

    def test_get_list_of_uploaded_files_for_authenticated_user(self):
        self.client.force_login(self.user)
        with patch("audio.models.set_s3_content_disposition_metadata"):
            AudioFile.objects.create(user=self.user, title="My file", file=create_dummy_file(), is_public=True)
            other_user = User.objects.create_user(email="other@a.com", password="pw")
            AudioFile.objects.create(user=other_user, title="Other user public file", file=create_dummy_file(),
                                     is_public=True)
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "My file")

    def test_get_list_of_public_files_for_unauthenticated_user(self):
        with patch("audio.models.set_s3_content_disposition_metadata"):
            user = User.objects.create(email='u@a.com', password='p')
            AudioFile.objects.create(user=user, title="My file", file=create_dummy_file(), is_public=True)
            AudioFile.objects.create(user=user, title="Other user public file", file=create_dummy_file(),
                                     is_public=True)
            AudioFile.objects.create(user=user, title="Other user private file", file=create_dummy_file(),
                                     is_public=False)
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class LatestAudioFilesViewTests(APITestCase):
    def setUp(self):
        self.latest_url = reverse("audio:audio-latest")
        self.user = User.objects.create_user(email="testlatest@example.com", password="password")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            self.audio_older_public = AudioFile.objects.create(user=self.user, title="Older Public Audio",
                                                               file=create_dummy_file("older.mp3"), is_public=True)
            time.sleep(0.01)
            AudioFile.objects.create(user=self.user, title="Middle Private Audio", file=create_dummy_file("middle.mp3"),
                                     is_public=False)
            time.sleep(0.01)
            self.audio_latest_public = AudioFile.objects.create(user=self.user, title="Latest Public Audio",
                                                                file=create_dummy_file("latest.mp3"), is_public=True)

    def test_get_latest_audio_files(self):
        response = self.client.get(self.latest_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 2)
        expected_titles_order = [self.audio_latest_public.title, self.audio_older_public.title]
        self.assertEqual([item["title"] for item in results], expected_titles_order)

    @patch("audio.models.set_s3_content_disposition_metadata")
    def test_get_latest_audio_files_pagination(self, mock_signal):
        for i in range(12):
            AudioFile.objects.create(user=self.user, title=f"Page Test {i}", file=create_dummy_file(f"p{i}.mp3"),
                                     is_public=True)
        response1 = self.client.get(self.latest_url, {"page": 1})
        self.assertEqual(len(response1.data['results']), 10)
        self.assertTrue(response1.data['has_more'])
        response2 = self.client.get(self.latest_url, {"page": 2})
        self.assertEqual(len(response2.data['results']), 4)
        self.assertFalse(response2.data['has_more'])


class AudioFileDetailViewTests(APITestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(email="owner@a.com", password="pw")
        self.other_user = User.objects.create_user(email="other@a.com", password="pw")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            self.public_audio = AudioFile.objects.create(user=self.owner_user, title="Public",
                                                         file=create_dummy_file("p.mp3"), is_public=True)
            self.private_audio = AudioFile.objects.create(user=self.owner_user, title="Private",
                                                          file=create_dummy_file("pr.mp3"), is_public=False)
        self.public_url = reverse("audio:audio-detail", kwargs={"uuid": self.public_audio.uuid})
        self.private_url = reverse("audio:audio-detail", kwargs={"uuid": self.private_audio.uuid})

    def test_get_public_audio_unauthenticated(self):
        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_private_audio_by_owner(self):
        self.client.force_login(self.owner_user)
        response = self.client.get(self.private_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_private_audio_by_other_user(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.private_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_counter_increments(self):
        self.assertEqual(self.public_audio.views, 0)
        self.client.get(self.public_url)
        self.public_audio.refresh_from_db()
        self.assertEqual(self.public_audio.views, 1)
        self.client.get(self.public_url)
        self.public_audio.refresh_from_db()
        self.assertEqual(self.public_audio.views, 2)


class AudioFileDeleteViewTests(APITestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(email="owner_del@a.com", password="pw")
        self.other_user = User.objects.create_user(email="other_del@a.com", password="pw")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            self.audio_to_delete = AudioFile.objects.create(user=self.owner_user, title="Delete Me",
                                                            file=create_dummy_file())
        self.delete_url = reverse("audio:audio-delete", kwargs={"uuid": self.audio_to_delete.uuid})

    def test_delete_audio_by_owner(self):
        self.client.force_login(self.owner_user)
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_audio_by_other_user(self):
        self.client.force_login(self.other_user)
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_audio_unauthenticated(self):
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AddLikeViewTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="liker1@a.com", password="pw")
        user2 = User.objects.create_user(email="liker2@a.com", password="pw")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            self.audio_file = AudioFile.objects.create(user=user2, title="Likeable", file=create_dummy_file())
        self.like_url = reverse("audio:audio-like", kwargs={"uuid": self.audio_file.uuid})
        self.client.force_login(self.user1)

    def test_add_like_success(self):
        response = self.client.post(self.like_url, {"is_liked": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Like.objects.filter(user=self.user1, is_liked=True).count(), 1)

    def test_change_like_to_dislike(self):
        Like.objects.create(user=self.user1, audio_file=self.audio_file, is_liked=True)
        response = self.client.post(self.like_url, {"is_liked": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Like.objects.get(user=self.user1, audio_file=self.audio_file).is_liked)

    def test_add_like_missing_is_liked_field(self):
        response = self.client.post(self.like_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLikedAudioFilesViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user_likes@a.com", password="pw")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            audio1 = AudioFile.objects.create(user=self.user, title="Liked 1", file=create_dummy_file())
            audio_disliked = AudioFile.objects.create(user=self.user, title="Disliked", file=create_dummy_file())
        Like.objects.create(user=self.user, audio_file=audio1, is_liked=True)
        Like.objects.create(user=self.user, audio_file=audio_disliked, is_liked=False)
        self.liked_url = reverse("audio:user-liked-audio")
        self.client.force_login(self.user)

    def test_get_liked_audio_files(self):
        response = self.client.get(self.liked_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn("Disliked", [d['title'] for d in response.data])


class AudioFileLikesCountViewTests(APITestCase):
    def setUp(self):
        with patch("audio.models.set_s3_content_disposition_metadata"):
            self.audio_file = AudioFile.objects.create(title="Countable", file=create_dummy_file())
        self.count_url = reverse("audio:audio-likes-count", kwargs={"uuid": self.audio_file.uuid})
        users = [User.objects.create_user(email=f"u{i}@a.com", password="pw") for i in range(3)]
        Like.objects.create(user=users[0], audio_file=self.audio_file, is_liked=True)
        Like.objects.create(user=users[1], audio_file=self.audio_file, is_liked=True)
        Like.objects.create(user=users[2], audio_file=self.audio_file, is_liked=False)

    def test_get_likes_count(self):
        response = self.client.get(self.count_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("likes"), 2)
        self.assertEqual(response.data.get("dislikes"), 1)


class TagListViewTests(APITestCase):
    def test_get_tag_list(self):
        tag1 = Tag.objects.create(name="Rock")
        Tag.objects.create(name="Pop")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            audio = AudioFile.objects.create(title="Song", file=create_dummy_file())
            audio.tags.add(tag1)
        response = self.client.get(reverse("audio:tag-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag_map = {item["name"]: item for item in response.data}
        self.assertEqual(tag_map["Rock"]["audio_count"], 1)
        self.assertEqual(tag_map["Pop"]["audio_count"], 0)


class AudioFilesByTagViewTests(APITestCase):
    def setUp(self):
        self.tag_rock = Tag.objects.create(name="Rock")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            rock_audio = AudioFile.objects.create(title="Rock Song", file=create_dummy_file("r.mp3"), is_public=True)
            rock_audio.tags.add(self.tag_rock)
            private_rock = AudioFile.objects.create(title="Private Rock", file=create_dummy_file("pr.mp3"),
                                                    is_public=False)
            private_rock.tags.add(self.tag_rock)

    def test_get_public_audio_by_tag(self):
        url = reverse("audio:audio-by-tag", kwargs={"tag_name": "Rock"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Rock Song")


class TopRatedAudioFilesViewTests(APITestCase):
    def setUp(self):
        self.top_rated_url = reverse("audio:audio-top-rated")
        user = User.objects.create_user(email="toprated@example.com", password="pw")
        with patch("audio.models.set_s3_content_disposition_metadata"):
            self.audio_most_likes = AudioFile.objects.create(user=user, title="Best Song Ever",
                                                             file=create_dummy_file("best.mp3"), is_public=True)
            self.audio_good_ratio = AudioFile.objects.create(user=user, title="Good Song",
                                                             file=create_dummy_file("good.mp3"), is_public=True)
            self.audio_zero_likes = AudioFile.objects.create(user=user, title="Meh Song",
                                                             file=create_dummy_file("meh.mp3"), is_public=True)
            self.audio_controversial = AudioFile.objects.create(user=user, title="Divisive Song",
                                                                file=create_dummy_file("divisive.mp3"), is_public=True)
            users = [User.objects.create_user(email=f"u{i}@a.com", password="pw") for i in range(5)]
            for u in users[:3]: Like.objects.create(user=u, audio_file=self.audio_most_likes, is_liked=True)
            for u in users[:4]: Like.objects.create(user=u, audio_file=self.audio_good_ratio, is_liked=True)
            Like.objects.create(user=users[4], audio_file=self.audio_good_ratio, is_liked=False)
            for u in users[:2]: Like.objects.create(user=u, audio_file=self.audio_controversial, is_liked=True)
            for u in users[2:4]: Like.objects.create(user=u, audio_file=self.audio_controversial, is_liked=False)

    def test_get_top_rated_order(self):
        response = self.client.get(self.top_rated_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        titles = [item['title'] for item in response.data]
        expected_order = ["Best Song Ever", "Good Song", "Divisive Song", "Meh Song"]
        self.assertEqual(titles, expected_order)

    def test_top_rated_with_search(self):
        response = self.client.get(self.top_rated_url, {'search': 'Song'})
        self.assertEqual(len([item['title'] for item in response.data]), 4)
        response = self.client.get(self.top_rated_url, {'search': 'Good'})
        self.assertEqual(len([item['title'] for item in response.data]), 1)