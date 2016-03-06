### Тестируем aiohttp с помощью простого чата
__Оглавление__
* *Введение*
* *Структура*
* *Роуты*
* *Handlers, Request and Response*
* *Настройки конфигурации*
* *Middlewares*
* *Базы данных*
* *Шаблоны*
* *Сессии, авторизация*
* *Статика*
* *WebSocket*
* *Выгрузка на Heroku*

---
__Введение__

Прошлой осенью мне удалось побывать на нескольких python митапах в Киеве. 
На одном из них выступал Николай Новик и рассказывал он о новом асинхронном 
фреймворке [aiohttp](http://aiohttp.readthedocs.org/en/stable/), 
работающем на библиотеке для асинхронных вызовов [asyncio](https://docs.python.org/3/library/asyncio.html) в 3 версии интерпретатора питона.
Данный фреймворк заинтересовал меня тем, что он создавался core python разработчиками, 
в основном Андреем Светловым из Киева и позиционировался как концепт python фреймворка для веба. 
Сейчас имеется огромное количество разных фреймворков, в каждом из которых своя философия, 
синтаксис и реализация общих для веба шаблонов. Я надеюсь, что со временем, все это разнообразие 
будет на одной основе - aiohttp.

__Структура__

Чтобы протестировать по максимуму все возможности aiohttp, я попытался разработать простой чат
на вебсокетах.Основой aiohttp является бесконечный loop, в котором крутятся handlers. 
Handler - так называемая сорутина, объект, который не блокирует ввод/вывод(I/O). 
Данный тип объектов появился в python 3.4 в библиотеке asyncio. Пока не произойдут все 
вычисления в данном объекте, он как бы засыпает, а в это время интерпретатор может обрабатывать 
другие объекты. Чтобы было понятно, наведу пример. Зачастую все задержки сервера происходят, 
когда он ожидает ответа от базы данных и пока этот ответ не придёт и не обработается, 
другие объекты ждут своей очереди. В данном случае другие объекты будут обрабатываться, 
пока не придёт ответ от базы. Но для реализации этого нужен асинхронный драйвер. 
На данный момент для aiohttp реализованы [ асинхронные драйвера и обёртки ]( https://github.com/aio-libs/ ) для большинства популярных баз данных ( [ postgresql ]( https://github.com/aio-libs/aiopg ), [ mysql ]( https://github.com/aio-libs/aiomysql ), [ redis ](https://github.com/aio-libs/aioredis)) 
Для mongodb есть [ Motor ]( http://motor.readthedocs.org/en/stable/ ), который я буду использовать в своём чате.

Точкой входа для моего чата служит файл [**app.py**](https://github.com/Crandel/aiohttp/blob/master/app.py). В нем создаётся объект app

```python
import asyncio
from aiohttp import web

loop = asyncio.get_event_loop()

app = web.Application(loop=loop, middlewares=[
    session_middleware(EncryptedCookieStorage(SECRET_KEY)),
    authorize,
    db_handler,
])
```
Как вы видите, при инициализации в app передаётся loop, а также список middleware, о котором я расскажу попозже.

__Роуты__

В отличии от flask на который aiohttp очень похож, роуты добавляются в уже инициализированное приложение app.
```python
app.router.add_route('GET', '/{name}', handler)
```
Вот кстати [ объяснение ] (http://asvetlov.blogspot.com/2014/10/flask_20.html) Светлова почему именно так реализовано.

Я вынес заполнение путей(route) в отдельный файл [routes.py](https://github.com/Crandel/aiohttp/blob/master/routes.py)
```python
from chat.views import ChatList, WebSocket
from auth.views import Login, SignIn, SignOut

routes = [
    ('GET', '/',        ChatList,  'main'),
    ('GET', '/ws',      WebSocket, 'chat'),
    ('*',   '/login',   Login,     'login'),
    ('*',   '/signin',  SignIn,    'signin'),
    ('*',   '/signout', SignOut,   'signout'),
]
```
Первый элемент - http метод, далее расположен url, третьим в кортеже идёт объект handler, 
и напоследок - имя пути, чтобы удобно было его вызывать в коде.

Далее я импортирую список routes в app.py и заполняю пути простым циклом пути в приложение
```python
from routes import routes

for route in routes:
        app.router.add_route(route[0], route[1], route[2], name=route[3])
```
Все просто и логично

__Handlers, Request and Response__

Я решил обработку запросов сделать по примеру Django фреймворка. В папке [auth](https://github.com/Crandel/aiohttp/tree/master/auth) находиться все, 
что касается пользователей, авторизации, обработка создания пользователя и его входа.
А в папке [chat](https://github.com/Crandel/aiohttp/tree/master/chat) находиться логика работы чата соответственно.
В aiohttp можно реализовать [handler](http://aiohttp.readthedocs.org/en/stable/web.html#handler) в качестве как функции, так и класса.
Я выбрал реализацию через класс
```python
class Login(web.View):

    async def get(self):
        session = await get_session(self.request)
        if session.get('user'):
            url = request.app.router['main'].url()
            raise web.HTTPFound(url)
        return b'Please enter login or email'
```
Про сессии я расскажу ниже, а все остальное думаю понятно и так. Хочу заметить,
что переадресация происходит либо возвратом(return) либо выбросом исключения в виде объекта
web.HTTPFound(), которому передаётся путь параметром.
Http методы в классе реализуются через асинхронные функции get, post и тд.
Есть некоторые особенности, если нужно работать с параметрами запроса.
```python
data = await self.request.post()
```

__Настройки конфигурации__

Все настройки я храню в файле [settings.py](https://github.com/Crandel/aiohttp/blob/master/settings.py).
Для хранения секретных данных я использую [envparse](https://github.com/rconradharris/envparse).
Данная утилита позволяет читать данные из переменных окружения а также парсить специальный файл, где эти переменные хранятся.
```python
if isfile('.env'):
    env.read_envfile('.env')
```
Во первых, мне это было неоходимо для поднятия проекта на Heroku, а во вторых, это оказалось еще и очень удобно,
я сначала использовал локальную базу, а потом тестировал на удаленной,
и переключение состояло из изменения всего одной строки в файле .env

__Middlewares__

При инициализации приложения можно задавать middleware. Я вынес их в отдельный [файл](https://github.com/Crandel/aiohttp/blob/master/middlewares.py).
Реализация стандартная - функция декоратор, в которой можна делать проверки или любые другие действия с запросом
*Пример проверки на авторизацию*
```python
async def authorize(app, handler):
    async def middleware(request):
        def check_path(path):
            result = True
            for r in ['/login', '/static/', '/signin', '/signout', '/_debugtoolbar/']:
                if path.startswith(r):
                    result = False
            return result

        session = await get_session(request)
        if session.get("user"):
            return await handler(request)
        elif check_path(request.path):
            url = request.app.router['login'].url()
            raise web.HTTPFound(url)
            return handler(request)
        else:
            return await handler(request)

    return middleware
```
Также я сделал middleware для подключения базы данных
```python
async def db_handler(app, handler):
    async def middleware(request):
        if request.path.startswith('/static/') or request.path.startswith('/_debugtoolbar'):
            response = await handler(request)
            return response

        request.db = app.db
        response = await handler(request)
        return response
    return middleware
```
Детали подключения ниже по тексту.

__Базы данных__

Для чата я использовал Mongodb и асинхронный драйвер Motor.
Подключение к базе происходит при инициализации приложения
```python
app.client = ma.AsyncIOMotorClient(MONGO_HOST)
app.db = app.client[MONGO_DB_NAME]
```
А закрытие соединения происходит в специальной функции shutdown
```python
async def shutdown(server, app, handler):

    server.close()
    await server.wait_closed()
    app.client.close()  # database connection close
    await app.shutdown()
    await handler.finish_connections(10.0)
    await app.cleanup()
```
Хочу заметить, что в случае асинхронного сервера нужно корректно завершить все паралельные задачи
```python
```
