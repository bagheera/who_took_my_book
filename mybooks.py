import cgi
import wsgiref.handlers
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from wtmb import *
from bookactions import *
###################################################################  
# global stuff
def post_process(f, after):
    def g(self):
        f(self)
        after(self)
    return g

def pre_process(f, before):
    def g(self, *args):
        before(self)
        f(self, *args)
    return g
###################################################################  
class BookListPage(webapp.RequestHandler):
  def get(self, *args):
    if self.request.path_info != '/mybooks':
       self.redirect('/mybooks')
    user = users.get_current_user()
    if user:
      logging.debug('creating logout url')
      url = users.create_logout_url("/mybooks")
      logging.debug(url)
      url_linktext = 'Logout'
      current_appuser = AppUser.getAppUserFor(AppUser(), user)
      others = current_appuser.others()
      listings = BookListing().listings_for(current_appuser, others, BookListing.show_tech_only(BookListing(), current_appuser))
      template_values = {
        'others': others,
        'current_user': current_appuser,
        "listings": listings,
        'url': url,
        'url_linktext': url_linktext
#        'nickname': NickName().wtmb_name_for(current_appuser)
        }
      path = os.path.join(os.path.dirname(__file__), 'books.html')
      self.response.out.write(template.render(path, template_values)) # render o/p can be cached
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
      self.redirect(users.create_login_url(self.request.uri))      
###################################################################
# putting this on hold  
#class NickName:
#    def wtmb_name_for(self, some_user):
#        if some_user.display_name() is None:
#            return '<input type="text" id="nickname" value="" title="In case you&apos;d like to be referred by a name different from your userid"/><a href="/nickname"> Set Nickname</a>
#        else:
#            return some_user.display_name()
###################################################################  
class BookListing:
  def tech_option(self, appuser):
    if self.show_tech_only(appuser):
        return '<a href="/show_all_books">See all books</a>'
    else:
        return '<a href="/show_tech_only">See tech books only </a>(experimental feature)'
        
  def tech_option_key_for(self, appuser):
    return "tech_option_key_for_" + str(appuser.key())

  def show_tech_only(self, appuser):
    return memcache.get(self.tech_option_key_for(appuser)) == "yes"

  def listings_for(self, me, others, show_tech_only):
      listing = "<h4>Books you own</h4>"
      listing += self.books_owned_by_me(me)
      listing += "<h4>Books you have borrowed</h4>"
      listing += self.books_borrowed_by(me)
      listing += "<h3>Others' Books</h3>"
      listing += self.tech_option(me)
      if show_tech_only:
          for user in others:
            listing += "<h4>" + user.googleUser.nickname() + " owns:</h4>"
            listing += self.tech_books_owned_by(user)
      else:
          for user in others:
            listing += "<h4>" + user.googleUser.nickname() + " owns:</h4>"
            listing += self.books_owned_by(user)
      return listing

  start_block_quote = "<blockquote>"
  start_block_quote_mine = "<blockquote class=\"mine\">"
  end_block_quote = "</blockquote>"
  line_break = "<br />"
  
  def books_owned_by(self, appUser):
    k = self.bo_listing_key(appUser)
    listing = memcache.get(k)
    if not listing:
      listing = self.start_block_quote
      for book in appUser.books_owned:
          listing += book.summary_loan()
          listing += book.transitions()
          listing += self.line_break
      listing += self.end_block_quote
      memcache.set(k, listing)
    return listing

  def technical(self, book):
    return book.is_technical
  
  def tech_books_owned_by(self, appUser):
    k = self.bo_tech_listing_key(appUser)
    listing = memcache.get(k)
    if not listing:
      listing = self.start_block_quote
      for book in filter(self.technical, appUser.books_owned):
          listing += book.summary_loan()
          listing += book.transitions()
          listing += self.line_break
      listing += self.end_block_quote
      memcache.set(k, listing)
    return listing
  
  def books_owned_by_me(self, appUser):
    k = self.bome_listing_key(appUser)
    listing = memcache.get(k)
    if not listing:
      listing = self.start_block_quote_mine
      for book in appUser.books_owned:
          listing += book.summary_loan()
          listing += book.transitions()
          listing += self.line_break
      listing += self.end_block_quote
      memcache.set(k, listing)
    return listing

  def books_borrowed_by(self, appUser):
    k = self.bb_listing_key(appUser)
    listing = memcache.get(k)
    if not listing:
      listing = self.start_block_quote_mine
      for book in appUser.books_borrowed:
          listing += book.summary_belong()
          listing += book.transitions()
          listing += self.line_break
      listing += self.end_block_quote
      memcache.set(k, listing)
    return listing

  def bo_listing_key(self, appUser):
    return 'listing_books_owned_by_' + str(appUser.key())

  def bo_tech_listing_key(self, appUser):
    return 'listing_tech_books_owned_by_' + str(appUser.key())

  def bome_listing_key(self, appUser):
    return 'listing_books_owned_by_me_' + str(appUser.key())

  def bb_listing_key(self, appUser):
    return 'listing_books_borrowed_by_' + str(appUser.key())
      
  def bo_listing_cache_reset(self, appUser):
    memcache.delete(self.bo_listing_key(appUser))
    memcache.delete(self.bo_tech_listing_key(appUser))

  def bome_listing_cache_reset(self, appUser):
    memcache.delete(self.bome_listing_key(appUser))

  def bb_listing_cache_reset(self, appUser):
    memcache.delete(self.bb_listing_key(appUser))
    
  def clear_cache(self, book):
    logging.info("clear_owner_cache for %s", book.owner.display_name())  
    self.bo_listing_cache_reset(book.owner)
    self.bome_listing_cache_reset(book.owner)
    # this won't clear borrow cache of abc when abc adds a book - which is correct
    if book.borrower:
      logging.info("clear_borrow_cache for %s", book.borrower.display_name())  
      self.bb_listing_cache_reset(book.borrower)    

Book.put = post_process(Book.put, BookListing().clear_cache)
Book.delete = pre_process(Book.delete, BookListing().clear_cache)
Book.change_borrower = pre_process(Book.change_borrower, BookListing().clear_cache)

###################################################################    
def real_main():
  application = webapp.WSGIApplication(
                                       [(r'/lookup_amz(.*)', Suggest),
                                        ('/mybooks', BookListPage),
                                        ('/addBook', AddToBookshelf),
                                        (r'/delete/(.*)', DeleteBook),
                                        (r'/borrow/(.*)', Borrow),
                                        (r'/return/(.*)', ReturnBook),
                                        (r'/lend/(.*)', Lend),
                                        (r'/lendTo/(.*)', LendTo),
                                        (r'/show_all_books', ShowAll),
                                        (r'/show_tech_only', ShowTechOnly),
                                        (r'(/?)(.*)', BookListPage)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

def profile_main():
 # This is the main function for profiling 
 # We've renamed our original main() above to real_main()
 import cProfile, pstats, StringIO
 prof = cProfile.Profile()
 prof = prof.runctx("real_main()", globals(), locals())
 stream = StringIO.StringIO()
 stats = pstats.Stats(prof, stream=stream)
 stats.sort_stats("time")  # Or cumulative
 stats.print_stats(80)  # 80 = how many to print
 # The rest is optional.
 # stats.print_callees()
 # stats.print_callers()
 #logging.debug("Profile data:\n%s", stream.getvalue())
 logging.info(memcache.get_stats())
              
if __name__ == "__main__":
  profile_main()
