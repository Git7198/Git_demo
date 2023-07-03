
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from config import comunity_token, acces_token
from core import VkTools
import psycopg2
from data_store import *


# отправка сообщений


class BotInterface():
    def __init__(self, comunity_token, acces_token):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(acces_token)
        self.params = {}
        self.worksheets = []
        self.offset = 0


    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

# обработка событий / получение сообщений

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text.lower() == 'привет':

                    '''Логика для получения данных о пользователе'''

                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(
                        event.user_id, f'Привет {self.params["name"]}')
                    if self.params['city'] is None:
                        self.get_city(event.user_id)
                    elif self.params['year'] is None:
                        self.get_year(event.user_id)
                elif event.text.lower() == 'поиск':

                    '''Логика для поиска анкет'''

                    self.message_send(
                        event.user_id, 'Приступаю к поиску')
                    if self.worksheets:
                        worksheet = self.worksheets.pop()
                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                    else:
                        self.worksheets = self.vk_tools.search_worksheet(
                            self.params, self.offset)
                        worksheet = self.worksheets.pop()

                        '''проверка анкеты в бд в соотвествие с event.user_id'''

                    with psycopg2.connect(database="matching", user="postgres", password="123456"):
                        if check_user(engine, event.user_id, worksheet["id"]) is True:
                            # worksheet = self.worksheets.pop()
                            continue

                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                        self.offset += 10

                    self.message_send(
                        event.user_id,
                        f'имя: {worksheet["name"]} ссылка: vk.com/id{worksheet["id"]}',
                        attachment=photo_string
                    )

                    '''добавить анкету в бд в соотвествие с event.user_id'''

                    with psycopg2.connect(database="matching", user="postgres", password="123456"):
                        add_user(engine, event.user_id, worksheet["id"])

                elif event.text.lower() == 'пока':
                    self.message_send(
                        event.user_id, 'До свидания.')
                else:
                    self.message_send(
                        event.user_id, 'Неизвестная команда. Используйте команды: Привет, Поиск, Пока')

    def get_city(self, user_id):
        self.message_send(user_id, 'Укажить город вашего проживания:')
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self.params['city'] = event.text
                self.message_send(event.user_id, 'Данные обновлены')
                break
    def get_year(self, user_id):
        self.message_send(user_id, 'Введите ваш возраст:')
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self.params['year'] = event.text
                self.message_send(event.user_id, 'Данные обновлены')
                break





if __name__ == '__main__':
    engine = create_engine(db_url_object)
    Base.metadata.create_all(engine)

    bot_interface = BotInterface(comunity_token, acces_token)
    bot_interface.event_handler()
