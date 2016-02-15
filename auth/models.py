from settings import USER_COLLECTION


class User():

    def __init__(self, db, data, **kw):
        print(kw)
        self.db = db
        self.collection = self.db[USER_COLLECTION]
        self.email = data.get('email')
        self.login = data.get('login')
        self.password = data.get('password')

    async def check_user(self, **kw):
        print(self.login, self.email)
        return await self.collection.find_one({'email': self.email})

    async def create_user(self, **kw):
        print(self.login, self.email, self.password)
        user = await self.check_user()
        if not user:
            result = await self.collection.insert({'email': self.email, 'login': self.login, 'password': self.password})
            print(result)
        else:
            result = b'User exists'
        return result
