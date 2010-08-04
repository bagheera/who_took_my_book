import cgi
import wsgiref.handlers
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from wtmb import *
from bookactions import *
from bookcache import *
from full import *

class BookListPage(webapp.RequestHandler):
  #args is necessary, but why?
  def get(self, *args):
    if self.request.path_info != '/mybooks':
       self.redirect('/mybooks')
    user = users.get_current_user()
    if user:
      url = users.create_logout_url('/thanks')
      url_linktext = 'Logout from Google'
      me = AppUser.getAppUserFor(user, self.request.get('u'), self.request.get('e')) #registers new user
      me.update_last_login()
      if me.just_created():
          next = SettingsPage()
          next.initialize(self.request, self.response)
          return next.get()
      template_values = {
        'url': url,
        'url_linktext': url_linktext,
        "username": me.display_name(),
        "groups": ', '.join(me.member_of)
      }
      path = os.path.join(os.path.dirname(__file__), 'books.html')
#      causing logout problems?
#      cache_for(self.response, 30)
      self.response.out.write(template.render(path, template_values)) # render o/p can be cached
    else:
      logging.info("new user from "+self.request.headers.get('Referer',"anon"))
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
      self.redirect(users.create_login_url(self.request.uri))
###################################################################    
class LendPage(webapp.RequestHandler):
  def get(self, what):
    template_values = {
      'book': Book.get(db.Key(what)),
    }
    path = os.path.join(os.path.dirname(__file__), 'lend.html')
    cache_for(self.response, 0, 6)
    self.response.out.write(template.render(path, template_values))

###################################################################    
class SettingsPage(webapp.RequestHandler):
  def get(self):
    me = AppUser.me()
    rows = []
    for group in Group.all():
        rows.append([group, 'checked' if me.belongs_to(group.name) else ''])
    template_values = {
        'rows': rows
    }
    path = os.path.join(os.path.dirname(__file__), 'usersettings')
    self.response.out.write(template.render(path, template_values))

#  have to purge cached books of this guy on group change
  def post(self):
        groups = self.request.get("membership")
        logging.info("groups: " + groups)
        if groups.strip() == '':
            groups = []
        else:
            groups = groups.split(',')
        AppUser.me().setMembership(groups)
###################################################################    
class WhatsNewFeed(webapp.RequestHandler):
  def get(self):
    self.response.headers['content-type'] = "application/atom+xml"
    self.response.headers['Cache-Control'] = "max-age=3600"
    self.response.out.write(CachedFeed.get())

def real_main():
  application = webapp.WSGIApplication(
                                       [(r'/lookup_amz(.*)', Suggest),
                                        ('/mybooks', BookListPage),
                                        ('/addBook', AddToBookshelf),
                                        (r'/delete/(.*)', DeleteBook),
                                        (r'/borrow/(.*)', Borrow),
                                        (r'/return/(.*)', ReturnBook),
                                        (r'/lend/(.*)', LendPage),
                                        (r'/lendTo', LendTo),
                                        ('/mybooksj', FullListing),
                                        ('/asin-import', ImportASINs),
                                        ('/nickname', Nickname),
                                        ('/feed/whats_new', WhatsNewFeed),
                                        ('/remind', Remind),
                                        ('/alluzers', AllUzers),
                                        ('/search', Search),
                                        ('/cron/keepalive', FullListing),
                                        ('/indexbook', IndexBook),
                                        ('/purgeInactive', PurgeInactiveUsers),
                                        ('/settings', SettingsPage),
                                        (r'(/?)(.*)', BookListPage)],
                                       debug = True)
  wsgiref.handlers.CGIHandler().run(application)

def profile_main():
    # This is the main function for profiling
    # We've renamed our original main() above to real_main()
    import cProfile, pstats, StringIO
    prof = cProfile.Profile()
    prof = prof.runctx("real_main()", globals(), locals())
    stream = StringIO.StringIO()
    stats = pstats.Stats(prof, stream=stream)
    stats.sort_stats("cumulative")  # Or cumulative
    stats.print_stats("whotookmybook")  # 80 = how many to print
    # The rest is optional.
    # stats.print_callees()
    # stats.print_callers()
    logging.info("Profile data:\n%s", stream.getvalue())
    
if __name__ == "__main__":
#  profile_main()
    real_main()