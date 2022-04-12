import tweepy
import logging
import os
from dotenv import load_dotenv
import logging
import re
import requests, json
from translate import Translator
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def load_environment():
    # Carrega variaveis de ambiente do .env no os.environ
    load_dotenv()

    return os.environ["CONSUMER_KEY"], os.environ["CONSUMER_SECRET"], \
           os.environ["ACCESS_TOKEN"], os.environ["ACCESS_TOKEN_SECRET"]

def create_api() -> tweepy.API:
    CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET = load_environment()

    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    # Create API object
    api = tweepy.API(auth, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        logger.error("Error creating API", exc_info=True)
        raise e
    return api

def get_weather_forecast(city_name):
    api_key = os.environ["WEATHER_API"]
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + api_key + "&q=" + city_name + "&units=metric"

    try:
        response = requests.get(complete_url)
        weather_json = response.json()

        if weather_json["cod"] == 200:
            temperatures = weather_json["main"]
            current_temperature = temperatures["temp"]
            current_humidity = temperatures["humidity"]
            weather_description = weather_json["weather"][0]["description"]

            return current_temperature, current_humidity, weather_description
        else:
            return None, None, None
    except:
        return None, None, None

def get_city(tweet_text):
    try:
        text = re.search("(?:\@[^\s]+)(.+)", tweet_text.lower()).group(1)
        return text.strip()
    except Exception as e:
        logger.error(f"Unable to find the city: {e}")
        return None

def make_tweet_msg(tweet_user, tweet_text):
    """
    @giow_bot santos
    return @{user_name} the forecast for {city} is {weather_forecast}
    """
    city_on_tweet = get_city(tweet_text)

    if city_on_tweet:
        current_temperature, current_humidity, weather_description = get_weather_forecast(city_on_tweet)
        if current_temperature:
            translator= Translator(to_lang="pt-br")
            try:
                weather_description_translated = translator.translate(weather_description)
            except:
                weather_description_translated = weather_description
            
            return f"@{tweet_user} @{tweet_user} A temperatura em {city_on_tweet} é 🌡️ {current_temperature} °C\nA humidade atual é 💧 {current_humidity}%\nCondição metereológica: {weather_description_translated}\n"
        # if city was not found
        else:
            return None

def check_mentions(api, since_id):
    logger.info("Retrieving mentions")
    new_since_id = since_id

    for tweet in tweepy.Cursor(api.mentions_timeline, since_id=since_id).items():
        new_since_id = max(tweet.id, new_since_id)

        if tweet.in_reply_to_status_id is not None:
            continue
        
        tweet_msg = make_tweet_msg(tweet.user.screen_name, tweet.text)
        if tweet_msg:
            api.update_status(
                status=tweet_msg,
                in_reply_to_status_id=tweet.id,
            )
    return new_since_id

if __name__ == "__main__":
    api = create_api()
    since_id = 1
    while True:
        with open("last_tweet_id.txt", "r") as file:
            since_id = int(file.read().strip())

        since_id = check_mentions(api, since_id)
        
        with open("last_tweet_id.txt", "w") as file:
            file.write(since_id)

        logger.info("Waiting...")
        time.sleep(60)