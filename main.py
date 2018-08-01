import pygame
import pygame.display
import pygame.mixer
import tagmsg
from pygame.locals import *
from app import *
from gui import *
from screen import *
from tagger import *
from utils import print_console
from blinker import signal


class TestScreen(Screen):
    main_panel = None
    health_bar = None
    shield_bar = None
    ammo_label = None
    msg_label = None
    health = 30.0
    max_health = 30.0
    tagger = None
    sound = None
    ammo_changed = None

    def __init__(self, root):
        Screen.__init__(self, 'Test')
        self.root = root

    def enter(self):
        print_console("Entering test screen")
        self.sound = pygame.mixer.Sound('fire.mp3')
        size = (320, 240)
        app_size = self.root.size
        title_color = (146, 218, 249)
        label_color = (145, 152, 162)
        panel = Panel('ui/PNG/metalPanel_blueCorner.slc', size[0], size[1])
        panel.position((app_size[0] / 2) - (size[0] / 2), (app_size[1] / 2) - (size[1] / 2))
        self.main_panel = panel
        self.root.add_object(self.main_panel)

        y_offset = 35
        height_offset = 30
        label_offset = 7
        padding = 10
        right_offset = 100
        font = pygame.font.Font("ui/Fonts/kenvector_future.ttf", 12)
        title = Label(font, "PyCoil", title_color)
        title.position(padding, 8)
        panel.add_object(title)

        bar_width = size[0] - padding - right_offset
        label = Label(font, "Shield", label_color)
        label.position(padding, y_offset + label_offset)
        panel.add_object(label)
        self.shield_bar = Bar('ui/blue_horizontal.bar', bar_width)
        self.shield_bar.position(right_offset, y_offset)
        panel.add_object(self.shield_bar)
        y_offset += height_offset

        label = Label(font, "Health", label_color)
        label.position(padding, y_offset + label_offset)
        panel.add_object(label)
        self.health_bar = Bar('ui/red_horizontal.bar', bar_width)
        self.health_bar.position(right_offset, y_offset)
        panel.add_object(self.health_bar)
        y_offset += height_offset

        # button = Button('ui/PNG/glassPanel.slc', 100, 30, font, "TEST HIT")
        # button.position(padding, y_offset)
        # panel.add_object(button)
        # button.set_callback(self.button_press)
        # y_offset += height_offset

        self.msg_label = Label(font, "Message: ", label_color)
        self.msg_label.position(padding, y_offset + label_offset)
        panel.add_object(self.msg_label)
        y_offset += height_offset

        self.ammo_label = Label(font, "Ammo: 0", label_color)
        self.ammo_label.position(padding, y_offset + label_offset)
        panel.add_object(self.ammo_label)

        tagmsg.on_ammo_changed.connect(self.ammo_changed)
        tagmsg.on_message.connect(self.message)

        self.tagger = TaggerService()
        self.tagger.try_connect()

    def message(self, sender, **kw):
        if 'msg' in kw:
            self.msg_label.set_text("Message: %s" % kw['msg'])

    def ammo_changed(self, sender, **kw):
        if 'ammo' in kw:
            self.ammo_label.set_text("Ammo: %d" % int(kw['ammo']))

    def update(self):
        Screen.update(self)
        self.tagger.update()
        # self.msg_label.set_text("Message: %s" % self.tagger.message)

    def button_press(self):
        self.health -= 1.0
        self.health_bar.set_percent(self.health / self.max_health)
        self.sound.play()

    def exit(self):
        self.root.remove_object(self.main_panel)


class PycoilApp(App):
    main_screen = None
    screen_manager = None

    def __init__(self):
        App.__init__(self)

    def setup(self):
        self.screen_manager = ScreenManager()
        self.main_screen = TestScreen(self)
        self.screen_manager.add_screen(self.main_screen)
        self.screen_manager.move_to('Test')
        self.add_object(self.screen_manager)


app = PycoilApp()
app.init_display()
app.set_bg_color((63, 124, 182))
app.setup()
app.run()
