from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
#from pytube import YouTube
import os
import assemblyai as aai
from openai import OpenAI
from .models import BlogPost

from yt_dlp import YoutubeDL
from decouple import config
from termcolor import colored

client = OpenAI(api_key=config("OPENAIKEY"))

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)


        # get yt title
        title = yt_title(yt_link)
        print(colored(title, 'yellow'))

        # get transcript
        transcription = get_transcription(yt_link)
        print(colored(transcription, 'green'))
        if not transcription:
            return JsonResponse({'error': " Failed to get transcript"}, status=500)


        # use OpenAI to generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        print(colored(blog_content, 'green'))
        if not blog_content:
            return JsonResponse({'error': " Failed to generate blog article"}, status=500)

        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()

        # return blog article as a response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

# def yt_title(link):
#     print(f"Link {link}")
#     yt = YouTube(link)
#     print(f"Title {title}")
#     title = yt.title
#     return title


def yt_title(link):
    info = YoutubeDL().extract_info(link, download=False)
    print(colored(info['title'], 'green'))
    return info['title']

def download_audio(link):
    # Ensure the MEDIA_ROOT directory exists
    media_root = settings.MEDIA_ROOT
    if not os.path.exists(media_root):
        os.makedirs(media_root)

    # Configure YoutubeDL options
    output_template = os.path.join(media_root, '%(title)s.mp3')
    ydl_opts = {
        'extract_audio': True,
        'format': 'bestaudio/best',
        'outtmpl': output_template,  # Save file to MEDIA_ROOT
       
    }

    # Use YoutubeDL to download the audio
    with YoutubeDL(ydl_opts) as video:
        info_dict = video.extract_info(link, download=True)
        video_title = info_dict['title']
        file_path = os.path.join(media_root, f"{video_title}.mp3")

        print(colored(f"Successfully Downloaded: {video_title}.mp3", 'green'))
        return file_path
        


def get_transcription(link):
    print(colored("Transcript Initiated", 'green'))
    audio_file = download_audio(link)
    aai.settings.api_key = config("AAIKEY")

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    print(colored(transcript.text, 'green'))
    return transcript.text

def generate_blog_from_transcription(transcription):

    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": prompt}
    ],
    max_tokens=1000
    )
  

    generated_content = response.choices[0].message.content
    print(colored(generated_content, 'green'))
    return generated_content



def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {'error_message': error_message})
        
    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message':error_message})
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message':error_message})
        
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')
