# backend/audio/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
import os
import json
import uuid
import time

from django.db.models.signals import post_save

from .models import AudioFile, Tag, Like

try:
    from value_object import ALLOWED_AUDIO_EXTENSIONS
except ImportError:
    ALLOWED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg']
    print("WARNING: Could not import ALLOWED_AUDIO_EXTENSIONS from value_object. Using default list for tests.")

User = get_user_model()


def create_dummy_file(filename="dummy_test_file.mp3", content=b"dummy content"):
    return SimpleUploadedFile(name=filename, content=content, content_type='audio/mpeg')


class AudioFileUploadTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.upload_url = reverse('audio:audio-upload')
        self.login_url = reverse('login')
        self.user_email = 'audiotester@example.com'
        self.user_password = 'testpassword123'
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            name='Audio Test User',
            is_active=True
        )
        self.login_data = {'email': self.user_email, 'password': self.user_password}
        if not ALLOWED_AUDIO_EXTENSIONS:
            self.test_audio_filename = "test_audio.mp3"
        elif ".mp3" in ALLOWED_AUDIO_EXTENSIONS:
            self.test_audio_filename = "test_audio.mp3"
        else:
            self.test_audio_filename = f"test_audio{ALLOWED_AUDIO_EXTENSIONS[0]}"
        self.test_audio_content = b"This is a small test audio file content."
        self.audio_file_to_upload = SimpleUploadedFile(
            name=self.test_audio_filename,
            content=self.test_audio_content,
            content_type='audio/mpeg'
        )
        self.valid_upload_data = {
            'title': 'Mój Super Utwór Testowy',
            'description': 'Opis mojego super utworu.',
            'is_public': 'true',
            'tags': ['TestTag1', 'Rock'],
        }

    def _login_client(self):
        login_response = self.client.post(self.login_url, self.login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK, "Pre-test login failed")
        self.assertTrue(self.client.cookies.get('access_token') or login_response.data.get('access_token'),
                        "Access token cookie/data not found after login for test client.")

    @patch.object(post_save, 'send')
    def test_upload_audio_success_authenticated(self, mock_post_save_send):
        self._login_client()
        form_data = self.valid_upload_data.copy()
        form_data['file'] = self.audio_file_to_upload
        response = self.client.post(self.upload_url, form_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Upload failed: {response.data}")
        self.assertTrue(AudioFile.objects.filter(title=self.valid_upload_data['title'], user=self.user).exists())
        audio_obj = AudioFile.objects.get(title=self.valid_upload_data['title'], user=self.user)
        self.assertEqual(response.data['title'], self.valid_upload_data['title'])
        self.assertTrue(response.data['is_public'])
        self.assertCountEqual(response.data['tags'], self.valid_upload_data['tags'])
        self.assertTrue(str(audio_obj.uuid) in response.data['file'])
        called_correctly = False
        for call_args_tuple in mock_post_save_send.call_args_list:
            named_args = call_args_tuple.kwargs
            if named_args.get('sender') == AudioFile and named_args.get('instance') == audio_obj:
                called_correctly = True
                break
        self.assertTrue(called_correctly,
                        "post_save.send was not called with AudioFile as sender and the correct instance. "
                        f"Actual calls: {mock_post_save_send.call_args_list}")

    def test_upload_audio_unauthenticated(self):
        form_data = self.valid_upload_data.copy()
        form_data['file'] = self.audio_file_to_upload
        response = self.client.post(self.upload_url, form_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Anon upload failed: {response.data}")
        self.assertTrue(AudioFile.objects.filter(title=self.valid_upload_data['title'], user=None).exists())

    def test_upload_audio_invalid_file_extension(self):
        self._login_client()
        invalid_file = SimpleUploadedFile(
            name="test_audio.txt",
            content=b"this is not an audio file",
            content_type='text/plain'
        )
        form_data = self.valid_upload_data.copy()
        form_data['file'] = invalid_file
        response = self.client.post(self.upload_url, form_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)
        self.assertTrue("Allowed audio file formats" in str(response.data['file'][0]))

    def test_upload_audio_missing_title(self):
        self._login_client()
        form_data_no_title = {
            'file': self.audio_file_to_upload,
            'description': 'Test description',
            'is_public': 'true'
        }
        response = self.client.post(self.upload_url, form_data_no_title, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        self.assertEqual(str(response.data['title'][0]), 'To pole jest wymagane.')

    def test_upload_audio_missing_file(self):
        self._login_client()
        form_data_no_file = self.valid_upload_data.copy()
        response = self.client.post(self.upload_url, form_data_no_file, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)
        self.assertEqual(str(response.data['file'][0]), 'Nie przesłano pliku.')


class LatestAudioFilesViewTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.latest_url = reverse('audio:audio-latest')
        self.user = User.objects.create_user(email='testlatest@example.com', password='password', name='LatestTestUser',
                                             is_active=True)
        AudioFile.objects.all().delete()
        with patch('audio.models.set_s3_content_disposition_metadata') as mock_signal_handler:
            self.audio_older_public = AudioFile.objects.create(user=self.user, title="Older Public Audio",
                                                               file=create_dummy_file("older.mp3"), is_public=True)
            time.sleep(0.01)
            self.audio_middle_private = AudioFile.objects.create(user=self.user, title="Middle Private Audio",
                                                                 file=create_dummy_file("middle.mp3"), is_public=False)
            time.sleep(0.01)
            self.audio_latest_public = AudioFile.objects.create(user=self.user, title="Latest Public Audio",
                                                                file=create_dummy_file("latest.mp3"), is_public=True)
            time.sleep(0.01)
            self.audio_very_latest_public = AudioFile.objects.create(user=self.user, title="Very Latest Public Audio",
                                                                     file=create_dummy_file("very_latest.mp3"),
                                                                     is_public=True)

    def test_get_latest_audio_files_first_page(self):
        response = self.client.get(self.latest_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        self.assertTrue(len(results) <= 10)
        expected_titles_order = [
            self.audio_very_latest_public.title,
            self.audio_latest_public.title,
            self.audio_older_public.title
        ]
        returned_titles = [item['title'] for item in results]
        public_audio_count = AudioFile.objects.filter(is_public=True).count()
        self.assertEqual(len(results), public_audio_count)
        self.assertEqual(returned_titles, expected_titles_order)
        self.assertNotIn(self.audio_middle_private.title, returned_titles)
        self.assertEqual(response.data.get('page'), 1)
        self.assertEqual(response.data.get('has_more'), False if public_audio_count <= 10 else True)

    @patch('audio.models.set_s3_content_disposition_metadata')
    def test_get_latest_audio_files_pagination(self, mock_signal_handler_pagination):
        for i in range(10):
            AudioFile.objects.create(user=self.user, title=f"Page Test Audio {i}",
                                     file=create_dummy_file(f"ptest{i}.mp3"), is_public=True)
            time.sleep(0.01)
        response_page1 = self.client.get(self.latest_url, {'page': 1}, format='json')
        self.assertEqual(response_page1.status_code, status.HTTP_200_OK)
        results_page1 = response_page1.data.get('results', [])
        self.assertEqual(len(results_page1), 10)
        self.assertTrue(response_page1.data.get('has_more'))
        self.assertEqual(response_page1.data.get('page'), 1)
        self.assertEqual(results_page1[0]['title'], "Page Test Audio 9")
        response_page2 = self.client.get(self.latest_url, {'page': 2}, format='json')
        self.assertEqual(response_page2.status_code, status.HTTP_200_OK)
        results_page2 = response_page2.data.get('results', [])
        self.assertEqual(len(results_page2), 3)
        self.assertFalse(response_page2.data.get('has_more'))
        self.assertEqual(response_page2.data.get('page'), 2)
        all_public_titles_newest_first = [
            a.title for a in AudioFile.objects.filter(is_public=True).order_by('-uploaded_at')]
        if len(all_public_titles_newest_first) > 10:
            self.assertEqual(results_page2[0]['title'], all_public_titles_newest_first[10])

    def test_get_latest_audio_files_empty(self):
        AudioFile.objects.all().delete()
        response = self.client.get(self.latest_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        self.assertEqual(len(results), 0)
        self.assertFalse(response.data.get('has_more'))
        self.assertEqual(response.data.get('page'), 1)


class AudioFileDetailViewTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.login_url = reverse('login')
        self.owner_user = User.objects.create_user(email='owner_detail@example.com', password='password',
                                                   name='Owner Detail User', is_active=True)
        self.other_user = User.objects.create_user(email='other_detail@example.com', password='password',
                                                   name='Other Detail User', is_active=True)
        self.owner_login_data = {'email': 'owner_detail@example.com', 'password': 'password'}
        with patch('audio.models.set_s3_content_disposition_metadata') as mock_signal:
            self.public_audio = AudioFile.objects.create(
                user=self.owner_user, title="Public Detail Test Audio",
                file=create_dummy_file("public_detail.mp3"), is_public=True
            )
            self.private_audio_owned = AudioFile.objects.create(
                user=self.owner_user, title="Private Owned Test Audio",
                file=create_dummy_file("private_owned.mp3"), is_public=False
            )
            self.private_audio_not_owned = AudioFile.objects.create(
                user=self.other_user, title="Private Not Owned Test Audio",
                file=create_dummy_file("private_not_owned.mp3"), is_public=False
            )
        self.public_audio_url = reverse('audio:audio-detail', kwargs={'uuid': self.public_audio.uuid})
        self.private_owned_audio_url = reverse('audio:audio-detail', kwargs={'uuid': self.private_audio_owned.uuid})
        self.private_not_owned_audio_url = reverse('audio:audio-detail',
                                                   kwargs={'uuid': self.private_audio_not_owned.uuid})
        self.non_existent_uuid = uuid.uuid4()
        self.non_existent_audio_url = reverse('audio:audio-detail', kwargs={'uuid': self.non_existent_uuid})

    def _login_as_owner(self):
        self.client.post(self.login_url, self.owner_login_data, format='json')

    def test_get_public_audio_unauthenticated(self):
        response = self.client.get(self.public_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.public_audio.title)

    def test_get_public_audio_authenticated_owner(self):
        self._login_as_owner()
        response = self.client.get(self.public_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.public_audio.title)

    def test_get_private_owned_audio_authenticated_owner(self):
        self._login_as_owner()
        response = self.client.get(self.private_owned_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.private_audio_owned.title)

    def test_get_private_owned_audio_unauthenticated(self):
        response = self.client.get(self.private_owned_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_private_not_owned_audio_authenticated_owner(self):
        self._login_as_owner()
        response = self.client.get(self.private_not_owned_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_audio_non_existent_uuid(self):
        self._login_as_owner()
        response = self.client.get(self.non_existent_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AudioFileDeleteViewTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.login_url = reverse('login')
        self.owner_user = User.objects.create_user(email='owner_delete@example.com', password='password',
                                                   name='Owner Delete User', is_active=True)
        self.other_user = User.objects.create_user(email='other_delete@example.com', password='password',
                                                   name='Other Delete User', is_active=True)
        self.owner_login_data = {'email': 'owner_delete@example.com', 'password': 'password'}
        with patch('audio.models.set_s3_content_disposition_metadata'):
            self.audio_to_delete = AudioFile.objects.create(
                user=self.owner_user, title="Audio To Delete",
                file=create_dummy_file("to_delete.mp3"), is_public=True
            )
            self.another_user_audio = AudioFile.objects.create(
                user=self.other_user, title="Another User Audio",
                file=create_dummy_file("other_user.mp3"), is_public=True
            )
        self.delete_url = reverse('audio:audio-delete', kwargs={'uuid': self.audio_to_delete.uuid})
        self.delete_another_url = reverse('audio:audio-delete', kwargs={'uuid': self.another_user_audio.uuid})
        self.delete_non_existent_url = reverse('audio:audio-delete', kwargs={'uuid': uuid.uuid4()})

    def _login_as_owner(self):
        self.client.post(self.login_url, self.owner_login_data, format='json')

    def test_delete_audio_by_owner_success(self):
        self._login_as_owner()
        initial_count = AudioFile.objects.count()
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AudioFile.objects.count(), initial_count - 1)
        self.assertFalse(AudioFile.objects.filter(uuid=self.audio_to_delete.uuid).exists())

    def test_delete_audio_by_another_authenticated_user(self):
        self._login_as_owner()
        initial_count = AudioFile.objects.count()
        response = self.client.delete(self.delete_another_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(AudioFile.objects.count(), initial_count)
        self.assertTrue(AudioFile.objects.filter(uuid=self.another_user_audio.uuid).exists())

    def test_delete_audio_unauthenticated(self):
        initial_count = AudioFile.objects.count()
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(AudioFile.objects.count(), initial_count)

    def test_delete_non_existent_audio(self):
        self._login_as_owner()
        initial_count = AudioFile.objects.count()
        response = self.client.delete(self.delete_non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(AudioFile.objects.count(), initial_count)


class AddLikeViewTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.login_url = reverse('login')
        self.user1 = User.objects.create_user(email='liker1@example.com', password='password', name='Liker One',
                                              is_active=True)
        self.user2 = User.objects.create_user(email='liker2@example.com', password='password', name='Liker Two',
                                              is_active=True)
        self.user1_login_data = {'email': 'liker1@example.com', 'password': 'password'}
        with patch('audio.models.set_s3_content_disposition_metadata'):
            self.audio_file = AudioFile.objects.create(
                user=self.user2,
                title="Likeable Audio",
                file=create_dummy_file("likeable.mp3"),
                is_public=True
            )
        self.like_url = reverse('audio:audio-like', kwargs={'uuid': self.audio_file.uuid})
        self.non_existent_audio_like_url = reverse('audio:audio-like', kwargs={'uuid': uuid.uuid4()})

    def _login_user1(self):
        self.client.post(self.login_url, self.user1_login_data, format='json')

    def test_add_like_success(self):
        self._login_user1()
        payload = {'is_liked': True}
        response = self.client.post(self.like_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_liked'])
        self.assertEqual(Like.objects.filter(user=self.user1, audio_file=self.audio_file, is_liked=True).count(), 1)

    def test_add_dislike_success(self):
        self._login_user1()
        payload = {'is_liked': False}
        response = self.client.post(self.like_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_liked'])
        self.assertEqual(Like.objects.filter(user=self.user1, audio_file=self.audio_file, is_liked=False).count(), 1)

    def test_change_like_to_dislike(self):
        self._login_user1()
        Like.objects.create(user=self.user1, audio_file=self.audio_file, is_liked=True)
        self.assertEqual(Like.objects.filter(user=self.user1, audio_file=self.audio_file, is_liked=True).count(), 1)
        payload = {'is_liked': False}
        response = self.client.post(self.like_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_liked'])
        self.assertEqual(Like.objects.filter(user=self.user1, audio_file=self.audio_file, is_liked=False).count(), 1)
        self.assertEqual(Like.objects.filter(user=self.user1, audio_file=self.audio_file, is_liked=True).count(), 0)

    def test_add_like_unauthenticated(self):
        payload = {'is_liked': True}
        response = self.client.post(self.like_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_like_missing_is_liked_field(self):
        self._login_user1()
        payload = {}
        response = self.client.post(self.like_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('is_liked', response.data)

    def test_add_like_non_existent_audio(self):
        self._login_user1()
        payload = {'is_liked': True}
        response = self.client.post(self.non_existent_audio_like_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UserLikedAudioFilesViewTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.login_url = reverse('login')
        self.liked_audio_url = reverse('audio:user-liked-audio')
        self.user1 = User.objects.create_user(email='user1_likes@example.com', password='password',
                                              name='User One Likes', is_active=True)
        self.user1_login_data = {'email': 'user1_likes@example.com', 'password': 'password'}
        self.user2 = User.objects.create_user(email='user2_nolikes@example.com', password='password',
                                              name='User Two NoLikes', is_active=True)
        with patch('audio.models.set_s3_content_disposition_metadata'):
            self.audio1 = AudioFile.objects.create(user=self.user2, title="Liked Audio 1",
                                                   file=create_dummy_file("liked1.mp3"), is_public=True)
            self.audio2 = AudioFile.objects.create(user=self.user2, title="Liked Audio 2",
                                                   file=create_dummy_file("liked2.mp3"), is_public=True)
            self.audio3_not_liked = AudioFile.objects.create(user=self.user2, title="Not Liked Audio",
                                                             file=create_dummy_file("notliked.mp3"), is_public=True)
            self.audio4_disliked = AudioFile.objects.create(user=self.user2, title="Disliked Audio",
                                                            file=create_dummy_file("disliked.mp3"), is_public=True)
        Like.objects.create(user=self.user1, audio_file=self.audio1, is_liked=True)
        Like.objects.create(user=self.user1, audio_file=self.audio2, is_liked=True)
        Like.objects.create(user=self.user1, audio_file=self.audio4_disliked, is_liked=False)

    def _login_user1(self):
        self.client.post(self.login_url, self.user1_login_data, format='json')

    def test_get_liked_audio_files_authenticated(self):
        self._login_user1()
        response = self.client.get(self.liked_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_titles = sorted([item['title'] for item in response.data])
        expected_titles = sorted([self.audio1.title, self.audio2.title])
        self.assertEqual(returned_titles, expected_titles)

    def test_get_liked_audio_files_no_likes(self):
        user2_login_data = {'email': 'user2_nolikes@example.com', 'password': 'password'}
        self.client.post(self.login_url, user2_login_data, format='json')
        response = self.client.get(self.liked_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_liked_audio_files_unauthenticated(self):
        response = self.client.get(self.liked_audio_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AudioFileLikesCountViewTests(APITestCase):
    # ... (kod tej klasy pozostaje bez zmian) ...
    def setUp(self):
        self.user1 = User.objects.create_user(email='counter1@example.com', password='password', name='Counter One',
                                              is_active=True)
        self.user2 = User.objects.create_user(email='counter2@example.com', password='password', name='Counter Two',
                                              is_active=True)
        with patch('audio.models.set_s3_content_disposition_metadata'):
            self.audio_file = AudioFile.objects.create(user=self.user1, title="Countable Audio",
                                                       file=create_dummy_file("countable.mp3"), is_public=True)
        self.likes_count_url = reverse('audio:audio-likes-count', kwargs={'uuid': self.audio_file.uuid})
        self.non_existent_audio_likes_url = reverse('audio:audio-likes-count', kwargs={'uuid': uuid.uuid4()})
        Like.objects.create(user=self.user1, audio_file=self.audio_file, is_liked=True)
        Like.objects.create(user=self.user2, audio_file=self.audio_file, is_liked=True)
        disliker = User.objects.create_user(email='disliker_count@example.com', password='password',
                                            name='Disliker Count', is_active=True)
        Like.objects.create(user=disliker, audio_file=self.audio_file, is_liked=False)

    def test_get_likes_count_success(self):
        response = self.client.get(self.likes_count_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('likes'), 2)
        self.assertEqual(response.data.get('dislikes'), 1)

    def test_get_likes_count_no_likes_or_dislikes(self):
        Like.objects.filter(audio_file=self.audio_file).delete()
        response = self.client.get(self.likes_count_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('likes'), 0)
        self.assertEqual(response.data.get('dislikes'), 0)

    def test_get_likes_count_non_existent_audio(self):
        response = self.client.get(self.non_existent_audio_likes_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# === NOWE KLASY TESTOWE PONIŻEJ ===

class TagListViewTests(APITestCase):
    """
    Test suite for TagListView (/api/audio/tags/).
    """

    def setUp(self):
        self.tags_url = reverse('audio:tag-list')
        self.tag1 = Tag.objects.create(name="Rock")
        self.tag2 = Tag.objects.create(name="Electronic")
        self.tag3 = Tag.objects.create(name="Jazz")

        user = User.objects.create_user(email='taglistuser@example.com', password='password', name='TagList User',
                                        is_active=True)
        with patch('audio.models.set_s3_content_disposition_metadata'):
            audio1 = AudioFile.objects.create(user=user, title="Rock Song", file=create_dummy_file("rock.mp3"))
            audio1.tags.add(self.tag1)
            audio2 = AudioFile.objects.create(user=user, title="Electronic Track",
                                              file=create_dummy_file("electro.mp3"))
            audio2.tags.add(self.tag2)
            audio3 = AudioFile.objects.create(user=user, title="Another Rock Song", file=create_dummy_file("rock2.mp3"))
            audio3.tags.add(self.tag1)

    def test_get_tag_list(self):
        """ Tests retrieving the list of all tags with audio counts. """
        response = self.client.get(self.tags_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Order of tags is not guaranteed unless specified in TagListView's queryset
        self.assertEqual(len(response.data), 3)

        tag_data_map = {item['name']: item for item in response.data}

        self.assertIn("Rock", tag_data_map)
        self.assertEqual(tag_data_map["Rock"]['audio_count'], 2)
        self.assertIn("Electronic", tag_data_map)
        self.assertEqual(tag_data_map["Electronic"]['audio_count'], 1)
        self.assertIn("Jazz", tag_data_map)
        self.assertEqual(tag_data_map["Jazz"]['audio_count'], 0)

    def test_get_tag_list_empty(self):
        """ Tests retrieving tag list when no tags exist. """
        Tag.objects.all().delete()
        AudioFile.objects.all().delete()  # Also delete audio files to ensure counts are 0
        response = self.client.get(self.tags_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class AudioFilesByTagViewTests(APITestCase):
    """
    Test suite for AudioFilesByTagView (/api/audio/tags/<tag_name>/).
    """

    def setUp(self):
        self.user = User.objects.create_user(email='tagfilteruser@example.com', password='password',
                                             name='TagFilter User', is_active=True)
        self.tag_rock = Tag.objects.create(name="Rock")
        self.tag_pop = Tag.objects.create(name="Pop")

        with patch('audio.models.set_s3_content_disposition_metadata'):
            self.rock_audio1 = AudioFile.objects.create(user=self.user, title="Rock Song 1",
                                                        file=create_dummy_file("rock1.mp3"), is_public=True)
            self.rock_audio1.tags.add(self.tag_rock)
            time.sleep(0.01)
            self.rock_audio2_private = AudioFile.objects.create(user=self.user, title="Rock Song 2 Private",
                                                                file=create_dummy_file("rock2priv.mp3"),
                                                                is_public=False)
            self.rock_audio2_private.tags.add(self.tag_rock)
            time.sleep(0.01)
            self.pop_audio1 = AudioFile.objects.create(user=self.user, title="Pop Song 1",
                                                       file=create_dummy_file("pop1.mp3"), is_public=True)
            self.pop_audio1.tags.add(self.tag_pop)
            time.sleep(0.01)
            self.rock_pop_audio = AudioFile.objects.create(user=self.user, title="Rock Pop Song",
                                                           file=create_dummy_file("rockpop.mp3"), is_public=True)
            self.rock_pop_audio.tags.add(self.tag_rock, self.tag_pop)

        self.rock_tag_url = reverse('audio:audio-by-tag', kwargs={'tag_name': "Rock"})
        self.pop_tag_url = reverse('audio:audio-by-tag', kwargs={'tag_name': "Pop"})
        self.non_existent_tag_url = reverse('audio:audio-by-tag', kwargs={'tag_name': "NonExistentTag"})

    def test_get_audio_files_by_rock_tag(self):
        """ Tests retrieving public audio files tagged with 'Rock'. """
        response = self.client.get(self.rock_tag_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_titles = [item['title'] for item in response.data]
        # Newest first based on setUp creation order and time.sleep()
        self.assertEqual(returned_titles[0], self.rock_pop_audio.title)
        self.assertEqual(returned_titles[1], self.rock_audio1.title)

    def test_get_audio_files_by_pop_tag(self):
        """ Tests retrieving public audio files tagged with 'Pop'. """
        response = self.client.get(self.pop_tag_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_titles = [item['title'] for item in response.data]
        # Newest first
        self.assertEqual(returned_titles[0], self.rock_pop_audio.title)
        self.assertEqual(returned_titles[1], self.pop_audio1.title)

    def test_get_audio_files_by_non_existent_tag(self):
        """ Tests retrieving audio files for a tag that does not exist or has no public audio. """
        response = self.client.get(self.non_existent_tag_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # View returns empty list, not 404
        self.assertEqual(len(response.data), 0)