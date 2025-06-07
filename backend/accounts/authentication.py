# backend/accounts/authentication.py
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import \
    AuthenticationFailed  # Importuj AuthenticationFailed z DRF

from .utils import \
    decode_token  # Zakładam, że decode_token jest w accounts/utils.py

User = get_user_model()


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token_to_decode = None
        auth_source = None  # Dla debugowania, skąd pochodzi token

        # 1. Spróbuj pobrać token z nagłówka Authorization (standard Bearer)
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token_to_decode = parts[1]
                auth_source = "header"
            # else:
            # Możesz tu dodać ostrzeżenie lub błąd, jeśli nagłówek jest, ale w złym formacie
            # print("JWTAuth: Malformed Authorization header")

        # 2. Jeśli nie ma tokena w nagłówku, spróbuj pobrać z ciasteczka 'access_token'
        if not token_to_decode:
            token_from_cookie = request.COOKIES.get("access_token")
            if token_from_cookie:
                token_to_decode = token_from_cookie
                auth_source = "cookie"

        # Jeśli nie znaleziono tokena ani w nagłówku, ani w ciasteczku
        if not token_to_decode:
            return None  # Brak danych uwierzytelniających, DRF spróbuje innych metod lub zwróci 401/403

        # 3. Zdekoduj i zweryfikuj token
        try:
            # decode_token powinien rzucać AuthenticationFailed w przypadku problemów z tokenem
            payload = decode_token(token_to_decode, expected_type="access")
            user_id = payload.get("user_id")
            if not user_id:
                raise AuthenticationFailed("Token payload does not contain user_id.")

            user = User.objects.get(id=user_id)
            if not user.is_active:  # Dodatkowe sprawdzenie, czy użytkownik jest aktywny
                raise AuthenticationFailed("User account is inactive.")

        except (
            AuthenticationFailed
        ) as e:  # Przechwyć wyjątki rzucone przez decode_token lub własne
            # print(f"JWTAuth: Authentication failed due to: {e} (source: {auth_source}, token: {token_to_decode[:20]}...)") # Logowanie błędu
            raise e  # Rzuć wyjątek dalej, aby DRF go obsłużył (np. zwracając 401)
        except User.DoesNotExist:
            # print(f"JWTAuth: User not found for user_id {user_id} from token (source: {auth_source}).") # Logowanie błędu
            raise AuthenticationFailed("User not found for the provided token.")
        except Exception as e:  # Inne nieoczekiwane błędy podczas autentykacji
            print(
                f"JWTAuth: Unexpected error during token authentication: {e} (source: {auth_source})"
            )  # Loguj błąd
            # Możesz rzucić AuthenticationFailed lub pozwolić na błąd 500, w zależności od polityki
            raise AuthenticationFailed(
                "An unexpected error occurred during authentication."
            )

        # Jeśli wszystko OK, zwróć użytkownika i token (lub None dla tokena, jeśli nie jest potrzebny dalej)
        # DRF oczekuje krotki (user, auth)
        # print(f"JWTAuth: User {user.email} authenticated successfully via {auth_source}.") # Logowanie sukcesu
        return (
            user,
            token_to_decode,
        )  # Możesz zwrócić token, jeśli inne części DRF go używają
