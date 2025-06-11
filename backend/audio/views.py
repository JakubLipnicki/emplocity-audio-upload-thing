from django.db.models import Count, ExpressionWrapper, F, FloatField, Q, Value
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import JWTAuthentication

from .models import AudioFile, Like, Tag
from .serializers import AudioFileSerializer, LikeSerializer, TagSerializer


class AudioFileUploadView(generics.CreateAPIView): 
    
    serializer_class = AudioFileSerializer
    permission_classes = [permissions.AllowAny] 
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


class LatestAudioFilesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        tags_to_filter = request.query_params.getlist("tags") 
        page_size = 10
        offset = (page - 1) * page_size

        queryset = AudioFile.objects.filter(is_public=True)

        if tags_to_filter:
            for tag_name in tags_to_filter:
                queryset = queryset.filter(tags__name__iexact=tag_name)
            queryset = queryset.distinct()

        queryset = queryset.order_by("-uploaded_at")
        
        total_count = queryset.count()
        results = list(queryset[offset: offset + page_size])
        
        serializer = AudioFileSerializer(results, many=True, context={'request': request})

        has_more = total_count > offset + page_size
        return Response(
            {
                "results": serializer.data,
                "has_more": has_more,
            }
        )

class UserUploadedAudioFilesView(generics.ListAPIView):
    
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AudioFileSerializer

    def get_queryset(self):
    
        return AudioFile.objects.filter(user=self.request.user).order_by(
            "-uploaded_at"
        )


class AudioFileDetailByUUIDView(generics.RetrieveAPIView):
    serializer_class = AudioFileSerializer
    lookup_field = "uuid"
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            # Użytkownik widzi publiczne pliki ORAZ swoje prywatne
            return AudioFile.objects.filter(Q(is_public=True) | Q(user=user))
        # Niezalogowany widzi tylko publiczne
        return AudioFile.objects.filter(is_public=True)

    def get_object(self):
        obj = super().get_object()
        obj.views = getattr(obj, "views", 0) + 1
        obj.save(update_fields=["views"])
        return obj


class AudioFileDeleteView(generics.DestroyAPIView):
    serializer_class = AudioFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    lookup_field = "uuid"

    def get_queryset(self):
        return AudioFile.objects.filter(user=self.request.user)


class AddLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, uuid):
        try:
            audio_file = AudioFile.objects.get(uuid=uuid)
        except AudioFile.DoesNotExist:
            raise NotFound("Audio file not found.")

        is_liked = request.data.get("is_liked")

        if is_liked is None:
            raise ValidationError({"is_liked": "This field is required."})

        # is_liked musi być booleanem
        if not isinstance(is_liked, bool):
            raise ValidationError({"is_liked": "This field must be a boolean."})

        like, created = Like.objects.update_or_create(
            user=request.user,
            audio_file=audio_file,
            defaults={"is_liked": is_liked},
        )

        serializer = LikeSerializer(like)
        return Response(serializer.data)


class UserLikedAudioFilesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AudioFileSerializer

    def get_queryset(self):
        liked_audio_ids = Like.objects.filter(
            user=self.request.user, is_liked=True
        ).values_list("audio_file_id", flat=True)
        return AudioFile.objects.filter(id__in=liked_audio_ids)


class AudioFileLikesCountView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, uuid):
        try:
            audio_file = AudioFile.objects.get(uuid=uuid)
        except AudioFile.DoesNotExist:
            raise NotFound("Audio file not found.")

        likes_count = audio_file.likes.filter(is_liked=True).count()
        dislikes_count = audio_file.likes.filter(is_liked=False).count()

        return Response(
            {
                "likes": likes_count,
                "dislikes": dislikes_count,
            }
        )


class TopRatedAudioFilesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        search_query = request.query_params.get("search", "")

        queryset = AudioFile.objects.filter(is_public=True)

        if search_query:
            queryset = queryset.filter(title__icontains=search_query)

        queryset = (
            queryset.annotate(
                likes_count=Count("likes", filter=Q(likes__is_liked=True)),
                dislikes_count=Count("likes", filter=Q(likes__is_liked=False)),
            )
            .annotate(
                # Dodajemy 1 do mianownika, aby uniknąć dzielenia przez zero
                like_ratio=ExpressionWrapper(
                    (1.0 * F("likes_count")) / (F("dislikes_count") + 1.0),
                    output_field=FloatField(),
                )
            )
            .order_by("-like_ratio", "-uploaded_at")
        )

        serializer = AudioFileSerializer(queryset, many=True)
        return Response(serializer.data)


class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]


class AudioFilesByTagView(APIView): # Changed from ListAPIView to APIView
    permission_classes = [permissions.AllowAny]

    def get(self, request, tag_name):
        page = int(request.query_params.get("page", 1))
        page_size = 10
        offset = (page - 1) * page_size

        # Base queryset filtered by tag name
        queryset = AudioFile.objects.filter(
            tags__name__iexact=tag_name, is_public=True
        ).order_by("-uploaded_at")

        total_count = queryset.count()
        results = list(queryset[offset : offset + page_size])

        # Pass request to serializer context to build full URLs for files
        serializer = AudioFileSerializer(results, many=True, context={'request': request})

        has_more = total_count > offset + page_size

        return Response(
            {
                "results": serializer.data,
                "has_more": has_more,
            }
        )