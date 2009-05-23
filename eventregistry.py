class BaseEvent(object):
    _subscriptions = {}

    def __init__(self, event_info = None):
        self.info = event_info

    def fire(self):
        for callback in self._subscriptions.get(self.__class__, []):
            callback(self.info)

    def subscribe(self, callback):
        if not callable(callback):
            raise Exception(str(callback) + 'is not callable')
        existing = self._subscriptions.get(self.__class__, None)
        if not existing:
            existing = set()
            self._subscriptions[self.__class__] = existing
        existing.add(callback)

class NewUserRegistered(BaseEvent):
    pass

class NewBookAdded(BaseEvent):
    pass

class BookDeleted(BaseEvent):
    pass

class BookReturned(BaseEvent):
    pass

class BookBorrowed(BaseEvent):
    pass

class BookLent(BaseEvent):
    pass
