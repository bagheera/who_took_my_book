from google.appengine.api.labs import taskqueue
from wtmb import Book

keycsv = ""
keylist = []
batches = []

for bk_key in Book.all_books():
    keylist.append(str(bk_key))

for i in range(0, len(keylist), 100):
    batches.append(keylist[i:i+100])

for batch in batches:
    taskqueue.add(url='/indexbook', params={'keycsv': ','.join(batch)})
