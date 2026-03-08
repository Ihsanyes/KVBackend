from rest_framework import serializers
from .models import *



class BrandSerilaizer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields =[
            'id',
            'name',
            'description',
            
            'created_at'
        ]