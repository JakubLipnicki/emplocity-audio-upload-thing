# backend/audio/tests.py
import os
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient  # APIClient jest już w APITestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile  # Do tworzenia fałszywych plików do testów
from unittest.mock import patch  # Do mockowania sygnału

from .models import AudioFile, Tag  # Importujemy modele z aplikacji audio
# Załóżmy, że value_object.py jest w katalogu backend/
# Jeśli jest gdzie indziej, dostosuj import
from value_object import ALLOWED_AUDIO_EXTENSIONS

User = get_user_model()


class AudioFileUploadTests(APITestCase):
    """
    Test suite for the AudioFileUploadView endpoint (/api/audio/upload/).
    """

    def setUp(self):
        self.upload_url = reverse('audio-upload')  # Nazwa z audio/urls.py
        self.login_url = reverse('login')  # Z accounts/urls.py

        self.user_email = 'audiouploader@example.com'
        self.user_password = 'testpassword123'
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            name='Audio Uploader User',
            is_active=True
        )
        self.login_data = {'email': self.user_email, 'password': self.user_password}

        # Przygotuj prosty, fałszywy plik audio dla testów
        # Upewnij się, że rozszerzenie jest na liście ALLOWED_AUDIO_EXTENSIONS
        # Weźmy pierwsze dozwolone rozszerzenie jako przykład
        if ALLOWED_AUDIO_EXTENSIONS:
            self.test_audio_extension = ALLOWED_AUDIO_EXTENSIONS[0].lower()  # np. '.mp3'
        else:
            self.test_audio_extension = ".mp3"  # Domyślne, jeśli lista jest pusta (co nie powinno mieć miejsca)

        self.test_audio_filename = f"test_audio{self.test_audio_extension}"
        # Tworzymy prosty plik bajtowy, nie musi to być prawdziwe audio dla testu uploadu
        self.audio_file_content = b"dummy audio content for testing"
        self.uploaded_file = SimpleUploadedFile(
            name=self.test_audio_filename,
            content=self.audio_file_content,
            content_type=f"audio/{self.test_audio_extension.lstrip('.')}"  # np. audio/mpeg dla .mp3
        )

        # Plik z niedozwolonym rozszerzeniem
        self.invalid_extension_file = SimpleUploadedFile(
            name="test_document.txt",
            content=b"this is not an audio file",
            content_type="text/plain"
        )

        self.valid_upload_data = {
            'title': 'My Test Upload Track',
            'description': 'A great test track.',
            'is_public': 'true',  # Twój widok obsługuje string "true"
            'tags': ['Test', 'Relax']  # Serializer oczekuje listy stringów
        }

    def _login_client(self):
        """ Logs in the test client using API and ensures cookies are set. """
        response = self.client.post(self.login_url, self.login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Pre-test login failed for audio tests.")
        # Sprawdź, czy ciasteczko access_token jest ustawione,
        # bo JWTAuthentication będzie go szukać
        self.assertTrue(self.client.cookies.get('access_token'),
                        "Access token cookie not set after login for audio tests.")

    # Mockujemy sygnał, aby uniknąć rzeczywistych operacji na S3/MinIO podczas testów jednostkowych/integracyjnych
    # Ścieżka do sygnału to miejsce, gdzie jest on zdefiniowany: 'audio.models.set_s3_content_disposition_metadata'
    @patch('audio.models.set_s3_content_disposition_metadata')
    def test_audio_upload_success_authenticated(self, mock_set_s3_metadata_signal):
        """
        Tests successful audio file upload by an authenticated user.
        Mocks the S3 metadata setting signal.
        """
        self._login_client()  # Uwierzytelnij klienta (ustawi ciasteczka)

        # Przygotuj dane do wysłania, włączając plik
        # Dla MultiPartParser, dane są wysyłane jako słownik, gdzie plik jest obiektem SimpleUploadedFile
        data_to_send = self.valid_upload_data.copy()
        data_to_send['file'] = self.uploaded_file

        # Użyj format='multipart' dla FileUpload
        response = self.client.post(self.upload_url, data_to_send, format='multipart')

        # Sprawdź status odpowiedzi
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Upload failed: {response.data}")

        # Sprawdź, czy plik został utworzony w bazie danych
        self.assertTrue(AudioFile.objects.filter(title=self.valid_upload_data['title'], user=self.user).exists())
        audio_obj = AudioFile.objects.get(title=self.valid_upload_data['title'], user=self.user)

        # Sprawdź, czy nazwa pliku na serwerze (w MinIO) to uuid.extension
        self.assertTrue(audio_obj.file.name.startswith(str(audio_obj.uuid)))
        self.assertTrue(audio_obj.file.name.endswith(self.test_audio_extension))

        # Sprawdź, czy tagi zostały dodane
        self.assertEqual(audio_obj.tags.count(), 2)
        tag_names = [tag.name for tag in audio_obj.tags.all()]
        self.assertIn('Test', tag_names)
        self.assertIn('Relax', tag_names)

        # Sprawdź, czy sygnał do ustawiania metadanych został wywołany
        # (ponieważ perform_create zapisuje obiekt, co powinno wywołać post_save)
        mock_set_s3_metadata_signal.assert_called_once()
        # Można by też sprawdzić argumenty, z którymi został wywołany sygnał, jeśli to potrzebne

        # Sprawdź dane w odpowiedzi
        self.assertEqual(response.data['title'], self.valid_upload_data['title'])
        # Link do pliku w odpowiedzi powinien być poprawnie skonstruowany przez serializer
        self.assertTrue(str(audio_obj.uuid) in response.data['file'])

    def test_audio_upload_unauthenticated(self):
        """
        Tests attempting to upload an audio file without authentication.
        """
        data_to_send = self.valid_upload_data.copy()
        data_to_send['file'] = self.uploaded_file

        # Klient jest domyślnie nieuwierzytelniony
        response = self.client.post(self.upload_url, data_to_send, format='multipart')

        # AudioFileUploadView ma JWTAuthentication, DRF powinien zwrócić 403 (lub 401)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('detail', response.data)
        self.assertEqual(str(response.data['detail']), "Nie podano danych uwierzytelniających.")

    @patch('audio.models.set_s3_content_disposition_metadata')
    def test_audio_upload_invalid_file_extension(self, mock_set_s3_metadata_signal):
        """
        Tests uploading a file with an invalid (not allowed) extension.
        """
        self._login_client()

        data_to_send = self.valid_upload_data.copy()
        data_to_send['file'] = self.invalid_extension_file  # Plik .txt

        response = self.client.post(self.upload_url, data_to_send, format='multipart')

        # Walidator validate_audio_file_extension powinien rzucić ValidationError,
        # co DRF przetłumaczy na 400 Bad Request.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)  # Błąd powinien dotyczyć pola 'file'
        # Sprawdź, czy komunikat błędu zawiera informację o dozwolonych formatach
        self.assertTrue("Allowed audio file formats" in str(response.data['file']))
        mock_set_s3_metadata_signal.assert_not_called()  # Sygnał nie powinien być wywołany, bo obiekt nie został zapisany

    @patch('audio.models.set_s3_content_disposition_metadata')
    def test_audio_upload_missing_title(self, mock_set_s3_metadata_signal):
        """
        Tests uploading an audio file without a title.
        """
        self._login_client()

        data_to_send = {  # Celowo pomijamy 'title'
            'description': 'Test track without title',
            'is_public': 'true',
            'file': self.uploaded_file
        }
        response = self.client.post(self.upload_url, data_to_send, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)  # Serializer powinien zgłosić brakujący 'title'
        mock_set_s3_metadata_signal.assert_not_called()

    # TODO: Dodać testy dla metody GET widoku AudioFileUploadView (listowanie plików użytkownika/publicznych)