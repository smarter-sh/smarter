"""Django http serializers for smarter api."""

from django.http import HttpRequest
from rest_framework import serializers

from smarter.lib.django.serializers import UserSerializer


class HttpRequestSerializer(serializers.Serializer):
    """Http request serializer for smarter api."""

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
            "method",
            "GET",
            "POST",
            "COOKIES",
            "META",
            "path",
            "encoding",
            "content_type",
        ]

    def create(self, validated_data):
        return HttpRequest(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance
