import requests
from django.shortcuts import render, redirect
from main_app.models import Book
from django.http import HttpResponse
from django.views.generic import ListView
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.conf import settings
from django.core.cache import cache
from time import sleep
from urllib.parse import quote
from django.contrib.auth.decorators import login_required
from django.contrib import messages

class Home(LoginView):
    template_name = 'home.html'

def about(request):
    return render(request, 'about.html')

def signup(request):
    error_message = ''
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            error_message = 'Invalid sign up - try again'
    else:
        form = UserCreationForm()
    context = {'form': form, 'error_message': error_message}
    return render(request, 'signup.html', context)

def bookshelf(request):
    books = Book.objects.filter(user=request.user)
    return render(request, 'books/bookshelf.html', { 'books': books })

def book_detail(request, book_id):
    book = Book.objects.get(id=book_id)
    return render(request, 'books/detail.html', {
        'bookshelf': bookshelf,
    })

def book_search(request):
    search_results = []
    error = None
    if 'q' in request.GET:
        query = request.GET.get('q', '')
        api_url = 'https://www.googleapis.com/books/v1/volumes'
        
        try:
            params = {
                'q': query,
                'key': settings.GOOGLE_BOOKS_API_KEY,
                'maxResults': '40'
            }
            
            print(f"Making request with API key: {settings.GOOGLE_BOOKS_API_KEY}")
            print(f"Full request URL: {api_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}")
            response = requests.get(api_url, params=params, timeout=10)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text[:500]}...")  
            
            if response.status_code == 200:
                data = response.json()
                print(f"Found {data.get('totalItems', 0)} total items")
                
                if 'items' in data:
                    for item in data['items']:
                        volume_info = item.get('volumeInfo', {})
                        image_links = volume_info.get('imageLinks', {})
                        
                        cover_url = image_links.get('thumbnail', '')
                        if cover_url:
                            cover_url = cover_url.replace('http://', 'https://')
                        
                        book_data = {
                            'id': item.get('id'),
                            'title': volume_info.get('title', ''),
                            'authors': ', '.join(volume_info.get('authors', [])),
                            'cover_url': cover_url,
                            'isbn_13': next((id.get('identifier') for id in volume_info.get('industryIdentifiers', []) 
                                          if id.get('type') == 'ISBN_13'), None),
                            'page_count': volume_info.get('pageCount', 0)
                        }
                        print(f"Processing book: {book_data['title']} by {book_data['authors']}")
                        search_results.append(book_data)
                else:
                    error = "No books found matching your search."
                    print("No items found in response")
            else:
                error = f"API Error: {response.status_code}"
                print(f"Error response: {response.text}")
                
        except requests.RequestException as e:
            error = f"Error fetching books: {str(e)}"
            print(f"Request error: {str(e)}")
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            print(f"Unexpected error: {str(e)}")
    
    return render(request, 'books/search.html', {
        'results': search_results,
        'error': error,
        'query': request.GET.get('q', '')
    })


@login_required
def book_add(request):
    if request.method == 'POST':
        google_books_id = request.POST.get('google_books_id')
        
        api_url = f'https://www.googleapis.com/books/v1/volumes/{google_books_id}'
        params = {
            'key': settings.GOOGLE_BOOKS_API_KEY
        }
        
        try:
            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                book_data = response.json()
                volume_info = book_data.get('volumeInfo', {})
                
                title = volume_info.get('title', '')
                if len(title) > 200:
                    title = title[:197] + '...'
                
                authors = volume_info.get('authors', [])
                author_string = ', '.join(authors)
                if len(author_string) > 200:
                    author_string = author_string[:197] + '...'
                
                book = Book.objects.create(
                    user=request.user,
                    title=title,
                    author=author_string,
                    cover_url=volume_info.get('imageLinks', {}).get('thumbnail', '').replace('http://', 'https://'),
                    isbn13=next((id.get('identifier') for id in volume_info.get('industryIdentifiers', []) 
                               if id.get('type') == 'ISBN_13'), None),
                    total_pages=volume_info.get('pageCount', 0),
                    status='plan_to_read'
                )
                
                messages.success(request, f'"{book.title}" has been added to your bookshelf!')
                return redirect('bookshelf')
            else:
                messages.error(request, 'Could not fetch book details. Please try again.')
        except Exception as e:
            messages.error(request, f'Error adding book: {str(e)}')
            print(f"Error in book_add: {str(e)}")
            print(f"Title length: {len(title)}")
            print(f"Author length: {len(author_string)}")
    
    return redirect('book-search')