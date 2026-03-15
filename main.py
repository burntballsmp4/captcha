from fastapi import FastAPI,Response,Depends
from pyrate_limiter import Duration, Limiter, Rate
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
import random
import string
from PIL import Image,ImageFont,ImageDraw
import io
import uuid
import redis
import numbers


app = FastAPI(title="Burntballs Captcha",summary="Burntballs Captcha API")

# local dragonflydb for perfomance tests
r = redis.Redis(host='localhost', port=6767, decode_responses=True)

# first cord number is X (width) and Y (height)
def gencaptcha():
    # generate random numbers, init images, init drawing modules and font
    key = random.randrange(111111,999999)
    capth = Image.new(mode="RGB", size=(200, 75))
    draw = ImageDraw.Draw(capth)
    font = ImageFont.truetype("microsoftsansserif.ttf", 60)

    # line coordinates
    linecord = random.randrange(10,60)
    cords = (0, linecord, 200, linecord)
    linecord2 = random.randrange(10,60)
    cords2 = (0, linecord2, 200, linecord2)

    # draw a line
    draw.line(cords, fill='white', width=2)
    draw.line(cords2, fill='white', width=2)

    # add some noise
    for i in range(1000):
        x = random.randrange(0, 200)
        y = random.randrange(0, 75)
        # make it random color noise
        draw.point((x, y), fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))


    # draw a random generated number
    draw.text((0, 0),str(key),(255,255,255),font=font)

    # generate UUID to go along with the captcha for verification later
    verifkey = str(uuid.uuid4())
    r.set(verifkey, key, ex=65)
    

    # save image in bytes for api to understand
    capd = io.BytesIO()
    capth.save(capd, format='JPEG')
    capd.seek(0) # rewind function
    return capd.getvalue(), verifkey

def verifiedtoken():
    # generate token 
    identification = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
    # store token in redis for 1 hour
    r.set(identification, "verified", ex=3600)
    # return token
    return identification


class verify(BaseModel):
    captchakey: str
    answer: int

class verifytoken(BaseModel):
    token: str

# initializate endpoint
@app.get("/getcap", dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(1, Duration.SECOND * 3))))],)
async def read_people():
    result, capverifkey = gencaptcha()
    return Response(content=result, headers={"X-Captcha-Key": capverifkey}, media_type="image/jpeg")
#start code with "fastapi dev main.py"

# verify captcha
@app.post("/verify", dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(1, Duration.SECOND * 2))))])
async def accepctans(verif: verify):
    # retrive what you got
    captchakey1 = verif.captchakey
    if len(captchakey1) != 36:
        return {"valid":"false"}
    
    answer1 = verif.answer
    checkanswer1 = isinstance(answer1, numbers.Number)
    if not checkanswer1:
        return{"valid":"false"}
    
    if len(answer1) != 6:
        return{"valid":"false"}
    
        # strategically placed to reduce redis load
    realans = r.get(captchakey1)
    if realans is None:
        return {"valid":"false"}
    else:
        if int(realans) == int(answer1):
         # delete key for no reuse
            print("delete redis key")
            r.delete(captchakey1)
            # generate a validated token for 1 hour
            verifiedtokn = verifiedtoken()
             # send it up
            return {"valid":"true", "token":verifiedtokn}
        else:
            # noob cant solve or invalid key
            print("invalid key or invalid solve")
            return {"valid":"false"}

@app.post("/verifytoken", dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(1, Duration.SECOND * 1))))])
async def accepctoken(verify: verifytoken):
    token = verify.token
    if len(token) != 128:
        return{"valid":"invalid_token"}
    
    if token is None:
        return {"valid":"invalid_token"}
    
    db = r.get(token)

    if token == db:
        return{"valid":"true"}
    else:
        return{"valid":"false"}