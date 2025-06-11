# pylint: disable=C0115
"""
Serializer classes for the Provider app.
"""

from smarter.apps.account.serializers import (
    AccountMiniSerializer,
    SecretSerializer,
    UserMiniSerializer,
)
from smarter.common.exceptions import SmarterException
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
    get_model_for_provider,
    get_models_for_provider,
    get_provider,
    get_providers,
)


class ProviderSerializer(SmarterCamelCaseSerializer):
    """PluginMeta model serializer."""

    owner = UserMiniSerializer(read_only=True)
    account = AccountMiniSerializer(read_only=True)
    api_key = SecretSerializer(read_only=True)

    class Meta:
        model = Provider
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "owner", "account"]

    def get_queryset(self):
        name = self.request.GET.get("name")
        if name:
            provider = get_provider(provider_name=name)
            return Provider.objects.filter(pk=provider.pk)

        try:
            providers = get_providers()
        except SmarterException:
            return Provider.objects.none()

        pks = [p.pk for p in providers]
        queryset = Provider.objects.filter(pk__in=pks)
        return queryset


class ProviderModelSerializer(SmarterCamelCaseSerializer):
    """ProviderModel model serializer."""

    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = ProviderModel
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "provider"]

    def get_queryset(self):

        name = self.request.GET.get("name")
        model_name = self.request.GET.get("model_name")

        if name and model_name:
            try:
                provider_model = get_model_for_provider(provider_name=name, model_name=model_name)
            except SmarterException:
                return ProviderModel.objects.none()
            return ProviderModel.objects.filter(pk=provider_model.pk)

        if name:
            try:
                provider_models = get_models_for_provider(provider_name=name)
            except SmarterException:
                return ProviderModel.objects.none()
            pks = [p.pk for p in provider_models]
            queryset = ProviderModel.objects.filter(pk__in=pks)
            return queryset

        queryset = ProviderModel.objects.filter(is_active=True)
        return queryset


class ProviderVerificationSerializer(SmarterCamelCaseSerializer):
    """ProviderVerification model serializer."""

    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = ProviderVerification
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "provider"]

    def get_queryset(self):
        name = self.request.GET.get("name")
        verification_type = self.request.GET.get("verification_type")

        if name:
            try:
                provider = get_provider(provider_name=name)
                queryset = ProviderVerification.objects.filter(provider=provider)
            except SmarterException:
                return ProviderVerification.objects.none()
            if verification_type:
                queryset = queryset.filter(verification_type__iexact=verification_type)
            return queryset

        queryset = ProviderVerification.objects.filter(is_active=True)
        return queryset


class ProviderModelVerificationSerializer(SmarterCamelCaseSerializer):
    """ProviderModelVerification model serializer."""

    provider_model = ProviderModelSerializer(read_only=True)

    class Meta:
        model = ProviderModelVerification
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "provider_model"]

    def get_queryset(self):
        try:
            provider_model = get_model_for_provider(
                provider_name=self.request.GET.get("name"), model_name=self.request.GET.get("model_name")
            )
        except SmarterException:
            return ProviderModelVerification.objects.none()

        queryset = ProviderModelVerification.objects.filter(provider_model=provider_model)
        verification_type = self.request.GET.get("verification_type")
        if verification_type:
            queryset = queryset.filter(verification_type__iexact=verification_type)
        return queryset
