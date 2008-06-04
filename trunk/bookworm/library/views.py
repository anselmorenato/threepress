from google.appengine.api import users

import logging, sys

from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response

from models import EpubArchive, HTMLFile, UserPrefs, StylesheetFile, unsafe_name
from forms import EpubValidateForm

def index(request):
    documents = EpubArchive.all()
    user = users.get_current_user()
    documents.filter('owner =', user)
    if not user:
        return render_to_response('login.html',  {'greeting': _greeting(), 'login':users.create_login_url('/')})

    return render_to_response('index.html', {'documents':documents, 'greeting':_greeting()})

def view(request, title, author):
    logging.info("Looking up title %s, author %s" % (title, author))
    document = _get_document(title, author)
    toc = HTMLFile.gql('WHERE archive = :parent ORDER BY order ASC', 
                   parent=document).fetch(100)
    
    return render_to_response('view.html', {'document':document, 'toc':toc})


def delete(request, title, author):
    logging.info("Deleting title %s, author %s" % (title, author))
    document = _get_document(title, author)
    toc = HTMLFile.gql('WHERE archive = :parent ORDER BY order ASC', 
                   parent=document).fetch(100)
    for t in toc:
        t.delete()
    document.delete()
    return index(request)
    
def view_chapter(request, title, author, chapter_id):
    logging.info("Looking up title %s, author %s, chapter %s" % (title, author, chapter_id))    
    document = _get_document(title, author)
    toc = HTMLFile.gql('WHERE archive = :parent ORDER BY order ASC', 
                   parent=document).fetch(100)
    chapter = HTMLFile.gql('WHERE archive = :parent AND idref = :idref',
                           parent=document, idref=chapter_id).get()

    userprefs = _prefs()
    # Did they switch viewing modes?
    if request.GET.has_key('iframe'):
        userprefs.use_iframe = (request.GET['iframe'] == 'yes')
        userprefs.put()
        
    return render_to_response('view.html', {'greeting':_greeting(),
                                            'document':document,
                                            'toc':toc,
                                            'use_iframe':userprefs.use_iframe,
                                            'chapter':chapter})

def view_chapter_frame(request, title, author, chapter_id):
    '''Generate an iframe to display the document online, possibly with its own stylesheets'''
    document = _get_document(title, author)
    chapter = HTMLFile.gql('WHERE archive = :parent AND idref = :idref',
                           parent=document, idref=chapter_id).get()    
    stylesheets = StylesheetFile.gql('WHERE archive = :parent',
                                     parent=document).fetch(10)
    return render_to_response('frame.html', {'document':document, 'chapter':chapter, 'stylesheets':stylesheets})

def view_stylesheet(request, title, author, stylesheet_id):
    document = _get_document(title, author)
    stylesheet = StylesheetFile.gql('WHERE archive = :parent AND idref = :idref',
                                    parent=document,
                                    idref=stylesheet_id).get()
    response = HttpResponse(content=stylesheet.file, content_type='text/css')
    response['Cache-Control'] = 'public'

    return response

def _get_document(title, author):
    document = EpubArchive.gql('WHERE title = :title AND author = :author AND owner = :owner',
                               owner=users.get_current_user(),
                               title=unsafe_name(title), 
                               author=unsafe_name(author)
                               ).get()
    if not document:
        raise Http404 
        
    return document

def upload(request):

    document = None 
    
    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)
        if form.is_valid():

            data = form.cleaned_data['epub'].content
            document_name = form.cleaned_data['epub'].filename
            logging.info("Document name: %s" % document_name)
            document = EpubArchive(name=document_name)
            document.content = data
            document.owner = users.get_current_user()
            document.put()
            try:
                document.explode()
                document.put()
            except:
                # If we got any error, delete this document
                document.delete()
                logging.error(sys.exc_info()[0])
                raise

            return HttpResponseRedirect('/')

    else:
        form = EpubValidateForm()        

    return render_to_response('upload.html', {'greeting':_greeting(),
                                              'form':form, 
                                              'document':document})



def _greeting():
    user = users.get_current_user()
    if user:
        return ("Signed in as %s (<a href=\"%s\">logout</a>)." % (user.nickname(), users.create_logout_url("/")))
    return ("<a href=\"%s\">Sign in or register</a>." % users.create_login_url("/"))

def _prefs():
    user = users.get_current_user()
    q = UserPrefs.gql("WHERE user = :1", user)
    userprefs = q.get()
    if not userprefs:
        # Create a preference object for this user
        userprefs = UserPrefs(user=user)
        userprefs.put()

    return userprefs

