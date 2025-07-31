from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    CustomTokenObtainPairSerializer, 
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer
)

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 登録後自動ログイン用のトークン生成
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'ユーザー登録が完了しました'
        }, status=status.HTTP_201_CREATED)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserProfileUpdateSerializer
        return UserProfileSerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def auth_status(request):
    """認証状態を確認するエンドポイント"""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': UserProfileSerializer(request.user).data
        })
    else:
        return Response({
            'authenticated': False,
            'message': 'ログインしていません'
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """ログアウト処理"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'ログアウトしました'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'ログアウトに失敗しました'}, status=status.HTTP_400_BAD_REQUEST)

def my_page(request):
    """マイページのHTMLテンプレート"""
    return render(request, 'accounts/my_page.html')

def register_page(request):
    """ユーザー登録ページのHTMLテンプレート"""
    return render(request, 'accounts/register.html')
