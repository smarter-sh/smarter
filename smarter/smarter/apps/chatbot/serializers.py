# pylint: disable=missing-docstring

from rest_framework import serializers

from smarter.apps.account.api.v0.serializers import AccountSerializer

from .models import ChatBot, ChatBotPlugin


class ChatBotSerializer(serializers.ModelSerializer):
    """Serializer for ChatBot model."""

    account = AccountSerializer()
    default_host = serializers.SerializerMethodField()
    default_url = serializers.SerializerMethodField()
    custom_host = serializers.SerializerMethodField()
    custom_url = serializers.SerializerMethodField()
    sandbox_host = serializers.SerializerMethodField()
    sandbox_url = serializers.SerializerMethodField()
    hostname = serializers.SerializerMethodField()
    scheme = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    url_chatbot = serializers.SerializerMethodField()
    url_chatapp = serializers.SerializerMethodField()

    class Meta:

        model = ChatBot
        fields = [
            "account",
            "name",
            "subdomain",
            "custom_domain",
            "deployed",
            "default_model",
            "default_temperature",
            "default_max_tokens",
            "app_name",
            "app_assistant",
            "app_welcome_message",
            "app_example_prompts",
            "app_placeholder",
            "app_info_url",
            "app_background_image_url",
            "app_logo_url",
            "app_file_attachment",
            "default_host",
            "default_url",
            "custom_host",
            "custom_url",
            "sandbox_host",
            "sandbox_url",
            "hostname",
            "scheme",
            "url",
            "url_chatbot",
            "url_chatapp",
        ]

    def get_default_host(self, obj):
        return obj.default_host

    def get_default_url(self, obj):
        return obj.default_url

    def get_custom_host(self, obj):
        return obj.custom_host

    def get_custom_url(self, obj):
        return obj.custom_url

    def get_sandbox_host(self, obj):
        return obj.sandbox_host

    def get_sandbox_url(self, obj):
        return obj.sandbox_url

    def get_hostname(self, obj):
        return obj.hostname

    def get_scheme(self, obj):
        return obj.scheme

    def get_url(self, obj):
        return obj.url

    def get_url_chatbot(self, obj):
        return obj.url_chatbot

    def get_url_chatapp(self, obj):
        return obj.url_chatapp


class ChatBotPluginSerializer(serializers.ModelSerializer):
    plugin = serializers.SerializerMethodField()

    class Meta:
        model = ChatBotPlugin
        fields = ["chatbot", "plugin_meta", "plugin"]

    def get_plugin(self, obj):
        return obj.plugin.to_json()  # Assuming `to_json` returns a serializable format
