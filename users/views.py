from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .permission import HasModulePermission, IsAdminOrSuperUser
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta


from .serializers import *
from .models import *


class LoginView(APIView):

    def post(self, request):
        serializer = LoginSerializer(data = request.data)

        if serializer.is_valid():
            employee_id = serializer.validated_data['employee_id']
            pin = serializer.validated_data['pin']

            try:
                user = User.objects.get(employee_id=employee_id)

                # check lock time
                if user.locked_until and user.locked_until > timezone.now():
                    return Response({
                        "status": "0",
                        "message": f"Account locked. Try after {user.locked_until}"
                    }, status=status.HTTP_403_FORBIDDEN)
    
                if user.check_password(pin):
                    user.failed_attempts = 0
                    user.locked_until = None
                    user.save()

                    refresh = RefreshToken.for_user(user)

                    return Response({
                        "status": "1",
                        "message": "Login successful",
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "id": user.id,
                        "employee_id": user.employee_id,
                        "role": user.role
                    }, status=status.HTTP_200_OK)
                else:
                    # Increment failed attempts
                    user.failed_attempts += 1
                    if user.failed_attempts >= 5:
                        user.locked_until = timezone.now() + timedelta(minutes=10)
                        user.failed_attempts = 0
                        user.save()

                        return Response({
                            "status": "0",
                            "message": "Account locked for 10 minutes"
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    user.save()
                    
                    return Response({
                        "status": "0",
                        "message": "Invalid PIN",
                        "remaining_attempts": 5 - user.failed_attempts
                    }, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                return Response({"status": "0", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CreateListEmployeeView(APIView):

    def post(self, request):
        serializer = EmployeeSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response({
                "status": "1",
                "message": "Employee created successfully",
                "employee_id": user.employee_id
            }, status=201)

        return Response(serializer.errors, status=400)
    
    def get(self, request):
        employees = User.objects.all()
        serializer = EmployeeSerializer(employees, many=True)

        return Response({
            "status": "1",
            "employees": serializer.data
        }, status=200)
    



class PreviewEmployeeIdView(APIView):

    def get(self, request):

        seq = EmployeeIdSequence.objects.first()

        if seq:
            next_number = seq.last_number + 1
        else:
            next_number = 1

        employee_id = f"EMP{str(next_number).zfill(4)}"

        return Response({
            "status": "1",
            "employee_id": employee_id
        })
    
class AssignPermissionView(generics.CreateAPIView):
    serializer_class = AssignPermissionSerializer
    permission_classes = [IsAdminOrSuperUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response({
            "status": "1",
            "message": "Permissions assigned successfully",
            "user_id": user.id
        }, status=201)