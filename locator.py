from locationsharinglib import Service, Person
from locationsharinglib.locationsharinglibexceptions import InvalidCookies
from geopy.distance import distance
from typing import List, Tuple
import requests
from config import gmaps_token
from models import get_coordinates
# import pytz
# from timezonefinder import TimezoneFinder
# from datetime import datetime


class MyService(Service):
    def _get_authenticated_session(self, cookies_file):
        try:
            session = self._get_session_from_cookie_file(cookies_file)
        except FileNotFoundError:
            message = 'Could not open cookies file, either file does not exist or no read access.'
            raise InvalidCookies(message) from None
        return session

# class MyPerson(Person):
#     tf = TimezoneFinder()
    
#     @property
#     def datetime(self):
#         """A datetime representation of the location retrieval."""
#         tz = self.tf.timezone_at(lat=self.latitude, lng=self.longitude)
#         return datetime.fromtimestamp(int(self.timestamp) / 1000, tz=pytz.timezone(tz))

def map_filter(coordinates: List[Tuple], length: int):
    points = [coordinates[0]]
    for point in coordinates:
        a = points[-1]
        b = point
        if distance(a, b).m > length:
            points.append(b)
    print(distance(a, b).m)
    return points

# def url_creator(coordinates: List[Tuple]):
#     """yandex url creator"""
#     start = ",".join([str(i) for i in coordinates[0]]) + ",flag"
#     end = ",".join([str(i) for i in coordinates[-1]]) + ",flag"
#     points = ""
#     for item in map_filter(coordinates):
#         for _ in item:
#             points += f'{str(_)},'
#     return f"https://static-maps.yandex.ru/1.x/?lang=en_US&size=650,450&l=map&spn=0.01,0.01&pt={start}~{end}&pl=w:1,{points[:-1]}"


def url_creator(coordinates, length):
    """google url creator"""
    points = ""
    start = "markers=size:mid|label:S|" + ",".join([str(i) for i in coordinates[0]])
    end = "markers=size:mid|label:E|" + ",".join([str(i) for i in coordinates[-1]])
    for item in map_filter(coordinates, length):
        pair = "|" + ",".join([str(i) for i in item])
        points += pair
    return f"https://maps.googleapis.com/maps/api/staticmap?language=ru&size=640x640&scale=2&key" \
           f"={gmaps_token}&{start}&{end}&path=color:0x0000ff|weight:2{points} "


def location_render(session, owner_id, nickname, timeframe, length):
    """
    Query DB for coordinates inside the timeframe. Create an URL with the coordinates and download the picture.
    For Yandex maps use (latitude, longitude) tuple. For Google maps use (longitude, latitude) tuple.
    :param length: Minimum distance between coordinates to take the coordinate into account.
    :param session: Database session.
    :param owner_id: Telegram user ID.
    :param nickname: Google maps nickname of the tracked object.
    :param timeframe: [start_date, end_date]
    :return: Binary picture data.
    """
    data = get_coordinates(session, owner_id, nickname, timeframe)
    coordinates = [(i.latitude, i.longitude) for i in data]
    url = url_creator(coordinates, length)
    result = requests.get(url)
    if result.status_code == 200:
        return result.content
