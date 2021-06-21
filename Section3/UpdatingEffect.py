
class UpdatingEffect():
    def __init__(self, duration):
        self.duration = duration
        self.active = True

    def start(self, owner = None):
        self.active = True

    def finish(self, owner = None):
        self.active = False

    def update(self, owner, dt):
        self.duration -= dt
        if self.duration <= 0:
            self.finish(owner)

    def cleanup(self):
        if self.active:
            self.finish()