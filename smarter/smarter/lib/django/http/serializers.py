"""Django http serializers for smarter api."""

from django.http import HttpRequest
from rest_framework import serializers

from smarter.lib.django.user import User


class UserSerializer(serializers.ModelSerializer):
    """User serializer for django request object serialization."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
        ]


class HttpRequestSerializer(serializers.Serializer):
    """Http request serializer for smarter api."""

    url = serializers.SerializerMethodField()
    method = serializers.CharField(max_length=10)
    GET = serializers.DictField(child=serializers.CharField())
    POST = serializers.DictField(child=serializers.CharField())
    COOKIES = serializers.DictField(child=serializers.CharField())
    META = serializers.DictField(child=serializers.CharField())
    path = serializers.CharField()
    encoding = serializers.CharField()
    content_type = serializers.CharField()
    user = UserSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        fields = [
            "url",
            "method",
            "GET",
            "POST",
            "COOKIES",
            "META",
            "path",
            "encoding",
            "content_type",
            "user",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["user"] = ret["user"]["username"]
        return ret

    def get_url(self, obj):
        if obj.request:
            _url = obj.request.build_absolute_uri()
            return _url
        return None

    def create(self, validated_data):
        return HttpRequest(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance
