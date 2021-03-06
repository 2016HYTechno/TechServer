from rest_framework import status, exceptions
from rest_framework.views import APIView
from rest_framework.response import Response
from techAPI.models import UserProfile, Crawler, Subscription, PushToken, Session
from techAPI.serializers import UserProfileSerializer, CrawlerSerializer, SubscriptionSerializer, PushTokenSerializer
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.http import HttpResponse
import re, json, random

class Auth():
    def verify_user(request):
        try:
            user_id=request.data['user_id']
            user_key=request.data['user_key']
        except:
            return False, -1, -1, "No 'user_id' or 'user_key'"

        try:
            if request.session['user_id'] != user_id or request.session['user_key']!=user_key:
                return False, -1, -1, "Invalid session"
        except:
            return False, -1, -1, "No have key in session"

        return True, user_id, user_key

    def email_auth(request, auth):
        result = {}
        try:
            user=UserProfile.objects.get(is_auth=auth)
        except:
            return HttpResponse("Invalid user or already authenticated")
        user.is_auth='True'
        user.save()
        return HttpResponse("Authenticated")

class ErrorResponse():
    def error_response(ErrorCode, message):
        data={"message":message, "ErrorCode":ErrorCode}
        return Response(data)

class ForgetPassword():
    def make_temp_password(self):
        Strings=['a','b','c','d','e','f','g','h','i','j','k','l','m','n','q','r','s',
                 't','u','v','w','x','y','z','0','1','2','3','4','5','6','7','8','9','0']
        password=''
        for i in range(0,8):
            password=password+Strings[random.randrange(0,35)]
        return password

    def send_temp_password(self, user_id):
        temp_password = ForgetPassword.make_temp_password()
        try:
            user= UserProfile.objects.get(user_id=user_id)
        except:
            return ErrorResponse.error_response(-1, "Invalid user")

        send_mail(
            '임시 비밀번호 입니다.',
            temp_password+' 로그인하여 비밀번호를 변경하세요',
            'bees1114@naver.com',
            [user_id],
        )
        user.password=make_password(password=temp_password, salt=None, hasher='default')
        user.save()
        data={"message":"Temp password sent", "ErrorCode":0}
        return HttpResponse(data)

class UserList(APIView):
    def make_auth_key(self):
        auth_key=''
        Strings = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'q', 'r', 's',
               't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9','0']
        for i in range(0, 15):
            auth_key = auth_key + Strings[random.randrange(0, 35)]
        return auth_key

    def get(self, request, format=None):
        users=UserProfile.objects.all()
        if users.count() == 0:
            return Response('No users')
        userSerializer = UserProfileSerializer(users, many=True)
        return Response(userSerializer.data)

    def post(self, request, format=None):
        data = request.data

        print(type(data)) #<class 'django.http.request.QueryDict'>
        print(data) #<QueryDict: {'password': ['@ㄹㅇㄹㄴ'], 'user_id': ['fsefvmek@naver.com'], 'name': ['oㄹㄴㄹ']}>

        if re.match(' /^[0-9a-zA-Z]([-_\.]?[0-9a-zA-Z])*@[0-9a-zA-Z]([-_\.]?[0-9a-zA-Z])*\.[a-zA-Z]{2,3}$/i',
                    data['user_id']) is not None:
            return ErrorResponse.error_response(-200, 'Invalid email address')
        exist=UserProfile.objects.filter(user_id = data['user_id'])
        print(exist)

        if exist.count() != 0:
            return ErrorResponse.error_response(-100, 'Already exist user_id')

        user = { }
        user['user_id'] = data['user_id']
        user['name'] =data['name']
        user['password'] = make_password(password=data['password'],salt=None,hasher='default')
        user['is_auth'] = self.make_auth_key()
        url = 'http://127.0.0.1:8000/email_auth/'+user['is_auth']+'/'
        userSerializer = UserProfileSerializer(data=user)
        print(userSerializer)
        print(userSerializer.get_fields())
        print(userSerializer.is_valid())
        print(userSerializer.errors)
        if userSerializer.is_valid():
            userSerializer.save()
            '''
            send_mail(
                '가입인증 메일입니다.',
                url+' 이 페이지를 클릭하여 사용자 인증을 하세요.',
                'bees1114@naver.com',
                [data['user_id']],
                fail_silently=False,
            )
            '''
            return_data={'message':'Success', 'ErrorCode':0}
            return Response(return_data)
        return ErrorResponse.error_response(-1, 'Error')

class UserDetail(APIView):
    def get_object(self, id):
        try:
            return UserProfile.objects.get(user_id=id)
        except UserProfile.DoesNotExist:
            return False

    def get(self, request, format=None):
        user_id=request.GET.get('user_id')
        user = self.get_object(id=user_id)
        if user == False:
            return ErrorResponse.error_response(-100, 'No user')
        #is_verified = Auth.verify_user(request=request)
        #if is_verified[0] == False:
        #    return Response(is_verified[3])
        userSerializer = UserProfileSerializer(user)
        return_data={'message':'Success', 'data':userSerializer.data, 'ErrorCode':0}
        return Response(return_data)

    def put(self, request, format=None):
        user_id=request.GET.get('user_id')
        user = self.get_object(id=user_id)
        if user == False:
            return Response("Invalid user", status=status.HTTP_400_BAD_REQUEST)
        data = request.data
        data['password'] = make_password(password=data['password'], salt=None, hasher='default')
        userSerializer = UserProfileSerializer(user, data=data)
        if userSerializer.is_valid():
            userSerializer.save()
            return Response(userSerializer.data)
        return Response(userSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, format=None):
        user_id=request.GET.get('user_id')
        user=self.get_object(id=user_id)
        if user == False:
            return Response("Invalid user", status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response(user_id + " deleted")

class CrawlerList(APIView):
    def get(self, request, format=None):
        user_info=Auth.verify_user(request=request)
        if not user_info[0]:
            return ErrorResponse.error_response(-1, "Invalid user")
        crawlers=Crawler.objects.all()
        if crawlers != None:
            crawlerSerializer=CrawlerSerializer(crawlers, many=True)
            return_data={"message":"Success", "crawlers":crawlerSerializer.data, 'ErrorCode':0}
            return Response(return_data)
        return ErrorResponse.error_response(-100, 'No crawler list')

    def post(self, request, format=None):
        crawlerSerializer=CrawlerSerializer(data=request.data)
        if crawlerSerializer.is_valid():
            crawlerSerializer.save()
            return Response(crawlerSerializer.data)
        return Response(crawlerSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CrawlerDetail(APIView):
    def get_object(self, name):
        try:
            return Crawler.objects.get(name=name)
        except Crawler.DoesNotExist:
            return False

    def get(self, request, name, format=None):
        crawler= self.get_object(name)
        if crawler != False:
            crawlerSerializer=CrawlerSerializer(crawler)
            return Response(crawlerSerializer.data)
        return Response("Invalid crawler", status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, name, format=None):
        crawler=self.get_object(name)
        if crawler == False:
            return Response("Invalid crawler", status=status.HTTP_400_BAD_REQUEST)
        crawlerSerializer=CrawlerSerializer(crawler, data=request.data)
        if crawlerSerializer.is_valid():
            crawlerSerializer.save()
            return Response(crawlerSerializer.data)
        return Response(crawlerSerializer.errors(), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, name, format=None):
        crawler=self.get_object(name)
        if crawler == False:
            Response("Invalid crawler", status=status.HTTP_400_BAD_REQUEST)
        crawler.delete()
        return Response(name+" deleted")

class SubscriptionList(APIView):
    def get(self, request, format=None):
        subscription=Subscription.objects.all()
        subscriptionSerializer=SubscriptionSerializer(subscription, many=True)
        return Response(subscriptionSerializer.data)

    def post(self, request, format=None):
        user_info=Auth.verify_user(request=request)
        if not user_info[0]:
            return ErrorResponse.error_response(-1, "Invalid user")
        subscriptionsSerializer=SubscriptionSerializer(data=request.data)
        if subscriptionsSerializer.is_valid():
            subscriptionsSerializer.save()
            return_data={"message":"success", "ErrorCode":0}
            return Response(return_data)
        return ErrorResponse.error_response(-1, "Error")

class SubscriptionDetail(APIView):
    def post(self, request, format=None):
        user_info=Auth.verify_user(request=request)
        if not user_info[0]:
            return ErrorResponse.error_response(-1, "Invalid user")

        user_id = request['user_id']
        if user_id != None:
            verified_user = Auth.verify_user(request=request)
            if verified_user[0] is False:
                return ErrorResponse.error_response(-100,"Not valid user")
            subscription = Subscription.objects.filter(user_id=user_id)
            if subscription.count() == 0:
                return Response(-200, "No subscriptions")
            subscriptionSerializer = SubscriptionSerializer(subscription, many=True)
        return_data={"message":'success', "subscriptions":subscriptionSerializer.data, 'ErrorCode':0}
        return Response(return_data)

    def delete(self, request, format=None):
        user_info=Auth.verify_user(request=request)
        if not user_info[0]:
            return ErrorResponse.error_response(-100, user_info[3])

        user_id=request.data['user_id']
        crawler_id=request.data['crawler_id']
        subscriptions = Subscription.objects.filter(user_id=user_id)
        if subscriptions == None :
            return ErrorResponse.error_response(-1, 'Invalid user_id')
        subscription = subscriptions.filter(crawler_id=crawler_id)

        if subscription == False:
            return Response(-1, "Invalid crawler_id")
        subscription.delete()
        return_data={"message":"success", "ErrorCode":0}
        return Response(return_data)

class PushTokenList(APIView):
    def get(self, request, format=None):
        token = PushToken.objects.all()
        tokenSerializer=PushTokenSerializer(token, many=True)
        return Response(tokenSerializer.data)

    def post(self, request, format=None):
        user_info = Auth.verify_user(request=request)
        if not user_info[0]:
            return ErrorResponse.error_response(-100, "Invalid user")

        tokenSerializer=PushTokenSerializer(data=request.data)
        if tokenSerializer.is_valid():
            tokenSerializer.save()
            return_data={"message":"success", "ErrorCode":0}
            return Response(return_data)
        return ErrorResponse.error_response(-1, "Error")

class PushTokenDetail(APIView):
    def get_object(self, id):
        try:
            return PushToken.objects.get(user_id=id)
        except PushToken.DoesNotExist:
            return False
    def get(self, request, id, format=None):
        token = self.get_object(id=id)
        if token != None:
            tokenSerializer=PushTokenSerializer(token)
            return Response(tokenSerializer.data)
        return Response("Invalid user-token", status= status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id, format=None):
        token = self.get_object(id)
        if token == False:
            return Response("Invalid user-token", status=status.HTTP_400_BAD_REQUEST)
        token.delete()
        return Response(token.user_id+ "`s " +token.token+ " deleted")

class Login(APIView):
    def make_user_key(self):
        Strings = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'q', 'r', 's',
                   't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

        user_key = ''
        for i in range(0, 15):
            user_key = user_key + Strings[random.randrange(0, 35)]
        return user_key

    def authenticate(self, user_id, password):
        try:
            user=UserProfile.objects.get(user_id=user_id)
        except:
            return -1
        chk_password=check_password(password=password, encoded=user.password)
        if chk_password is False:
            return -2
        return user

    def post(self, request):
        try:
            user_id=request.data['user_id']
        except Exception as e:
            return_data={'message':'No user_id', 'ErrorCode':-1}
            return Response(return_data)
        try:
            password=request.data['password']
        except Exception as e:
            return_data={'message':'No password', 'ErrorCode':-1}
            return Response(return_data)
        try:
            user_key = request.session['user_key']
        except:
            user_key = 'asdf'

        user=self.authenticate(user_id=user_id, password=password)
        if UserProfile.objects.get(user_id=user_id).is_authenticated() is not True:
            return_data={'message':'Need authentication', 'ErrorCode':-300}
            return Response(return_data)
        if user is -1:
            return_data={'message':'Invalid user', 'ErrorCode':-100}
            return Response(return_data)
        elif user is -2:
            return_data={'message':'Invalid password', 'ErrorCode':-200}
            return Response(return_data)

        else:
            request.session['user_key'] = user_key
            request.session['user_id'] = user_id
            data = {'user_key':user_key, 'user_id':user_id, 'message':"Login success", 'ErrorCode':0}
            return Response(data)

class ChangePassword(APIView):
    def post(self, request):
        try:
            user_id=request.data['user_id']
        except:
            return ErrorResponse.error_response(-1, "No user_id")
        try:
            password=request.data['password']
        except:
            return ErrorResponse.error_response(-1, "No current password")
        try:
            new_password=request.data['new_password']
        except:
            return ErrorResponse.error_response(-1, "No new_password")
        user=UserProfile.objects.get(user_id=user_id)
        chk_password=check_password(password=password, encoded=user.password)
        if chk_password is False:
            return ErrorResponse.error_response(-100, "Not correct current password")
        user.password=make_password(password=new_password, salt=None, hasher='default')
        user.save()
        return_data={"message":"success","ErrorCode":0}
        return Response(return_data)

class SubscriberPushToken(APIView):
    def post(self, request):
        try:
            subscriber=Subscription.objects.filter(crawler_id=request.data['crawler_id'])
        except:
            data={'return_code':-100, 'message':'Invalid crawler_id'}
            return Response(data)
        #data={'subscriber':subscriber[0].user_id}
        #return Response(data)
        total=[]
        for subs in subscriber:
            push_token=PushToken.objects.filter(user_id=subs.user_id)
            for pushtoken in push_token:
                arr = {'user_id': pushtoken.user_id, 'push_token': pushtoken.push_token}
                total.append(arr)

        #except:
        #    data={'return_code':-200, 'message':'No subscriber'}
        #    return Response(data)
        data={'return_code':0, 'data':total}
        return Response(data)