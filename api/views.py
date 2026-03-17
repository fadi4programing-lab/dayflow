from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import Task, Goal, TimeBlock, Note, Event, CalendarTask
from .serializers import (
    UserSerializer, RegisterSerializer, TaskSerializer,
    GoalSerializer, TimeBlockSerializer, NoteSerializer,
    EventSerializer, CalendarTaskSerializer
)


# ── AUTH ──────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ── TASKS ─────────────────────────────────────────

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)


# ── GOALS ─────────────────────────────────────────

class GoalListCreateView(generics.ListCreateAPIView):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


# ── TIME BLOCKS ───────────────────────────────────

class TimeBlockListCreateView(generics.ListCreateAPIView):
    serializer_class = TimeBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TimeBlock.objects.filter(user=self.request.user).order_by('date', 'start_time')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TimeBlockDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TimeBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TimeBlock.objects.filter(user=self.request.user)


# ── NOTES ─────────────────────────────────────────

class NoteListCreateView(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)


# ── EVENTS ────────────────────────────────────────

class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user).order_by('date', 'start_time')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)


# ── CALENDAR TASKS ────────────────────────────────

class CalendarTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = CalendarTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CalendarTask.objects.filter(
            user=self.request.user
        ).select_related('task').order_by('date')

        # Filter by date if provided — /api/calendar/?date=2026-03-12
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CalendarTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CalendarTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CalendarTask.objects.filter(user=self.request.user)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
        })
    return Response({'error': 'Invalid username or password'}, status=400)