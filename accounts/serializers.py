from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'username'  # usernameでログイン
    
    def validate(self, attrs):
        # usernameでの認証に変更
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('ユーザー名またはパスワードが正しくありません')
            if not user.is_active:
                raise serializers.ValidationError('ユーザーアカウントが無効になっています')
        
        # 元のvalidateメソッドを呼び出し
        return super().validate(attrs)
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # カスタムクレームを追加
        token['username'] = user.username
        token['user_id'] = user.id
        if user.email:
            token['email'] = user.email
        
        return token

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        help_text="パスワードは8文字以上で、数字のみは不可"
    )
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'password', 'password_confirm', 'email', 
                 'first_name', 'last_name', 'bio', 'favorite_genre', 
                 'reading_time_preference')
        extra_kwargs = {
            'username': {'help_text': 'ログイン用のユーザー名（半角英数字推奨）'},
            'email': {'required': False, 'help_text': 'メールアドレス（任意）'},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("パスワードが一致しません")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'bio', 'favorite_genre', 'reading_time_preference',
                 'date_joined', 'created_at', 'updated_at')
        read_only_fields = ('id', 'username', 'date_joined', 'created_at', 'updated_at')

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'bio', 
                 'favorite_genre', 'reading_time_preference') 