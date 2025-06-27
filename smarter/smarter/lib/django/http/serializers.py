"""Django http serializers for smarter api."""

from django.http import HttpRequest
from rest_framework import serializers

from smarter.apps.account.models import UserClass as User


class UserSerializer(serializers.ModelSerializer):
    """User serializer for django request object serialization."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
        ]


class HttpAnonymousRequestSerializer(serializers.Serializer):
    """Http anonymous request serializer for smarter api."""

    url = serializers.SerializerMethodField()
    method = serializers.CharField(max_length=10)
    GET = serializers.DictField(child=serializers.CharField())
    POST = serializers.DictField(child=serializers.CharField())
    COOKIES = serializers.DictField(child=serializers.CharField())
    META = serializers.DictField(child=serializers.CharField())
    path = serializers.CharField()
    encoding = serializers.CharField()
    content_type = serializers.CharField()

    # pylint: disable=missing-class-docstring
    class Meta:
        fields = "__all__"
        extra_kwargs = {
            "url": {"required": False},
            "method": {"required": False},
            "GET": {"required": False},
            "POST": {"required": False},
            "COOKIES": {"required": False},
            "META": {"required": False},
            "path": {"required": False},
            "encoding": {"required": False},
            "content_type": {"required": False},
        }
        model = HttpRequest

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["url"] = self.get_url(instance)
        return ret

    def get_url(self, obj):
        if obj and hasattr(obj, "request") and obj.request:
            _url = obj.request.build_absolute_uri() if hasattr(obj.request, "build_absolute_uri") else None
            return _url
        return None

    def create(self, validated_data) -> HttpRequest:
        req = HttpRequest()
        for attr, value in validated_data.items():
            setattr(req, attr, value)
        return req

    def update(self, instance: HttpRequest, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance


class HttpAuthenticatedRequestSerializer(HttpAnonymousRequestSerializer):
    """Http authenticated request serializer for smarter api."""

    user = UserSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        fields = "__all__"
        read_only_fields = fields
        extra_kwargs = {
            "user": {"required": False},
        }
        model = HttpRequest

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["user"] = ret["user"]["username"]
        return ret
