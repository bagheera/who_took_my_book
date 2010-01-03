# introduce nickname on old users

from google.appengine.ext import db
from wtmb import *
import logging

Group(name="tw_blore", createdBy="sriram", description="ThoughtWorks Bangalore").put()
Group(name="tw_chennai", createdBy="sriram", description="ThoughtWorks Chennai").put()
Group(name="tw_pune", createdBy="sriram", description="ThoughtWorks Pune").put()
Group(name="f12", createdBy="sriram", description="private group").put()

tw_blore = ['tw_blore']
for user in AppUser.all().fetch(100):
    user.setMembership(tw_blore)
    user.put()
