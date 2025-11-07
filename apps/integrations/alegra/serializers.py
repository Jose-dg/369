from rest_framework import serializers

class ResendInvoiceSerializer(serializers.Serializer):
    pos_invoice_name = serializers.CharField(max_length=100, required=True)
