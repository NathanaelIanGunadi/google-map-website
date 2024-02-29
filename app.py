from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from source.scraper import GoogleMapScraper
from flask_googlemaps import GoogleMaps, Map
import bcrypt
from datetime import timedelta

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
app = Flask(__name__)
app.secret_key = 'TeLLMEWHY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db.init_app(app)
login_manager.init_app(app)

GOOGLE_KEY = "AIzaSyDbbDAUExwpzu7IaZ1h_Xw5-i6P2jwtXXs"
GOOGLE_MAP_KEY = "AIzaSyBKOqBE1tCLB4_ruwU8WVyCuDRN0exE_xo"
GoogleMaps(app, key=GOOGLE_MAP_KEY)

salt = bcrypt.gensalt()

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False
def add_japanese(keyword_list):
    if "restaurant" in keyword_list:
        keyword_list.insert(0, "飲食店")
    if "bar" in keyword_list:
        keyword_list.insert(0, "バー")
    if "karaoke" in keyword_list:
        keyword_list.insert(0, "カラオケ")

def change_to_japanese(info):
    if info['type_of_place'] == "restaurant":
        info['type_of_place'] = "飲食店"
    if info['type_of_place'] == "bar":
        info['type_of_place'] = "バー"
    if info['type_of_place'] == "karaoke":
        info['type_of_place'] = "カラオケ"

def get_results_and_markers(places):
    results = {place.name: {'rating': place.rating, 'price_level': place.price_level * "¥" if place.price_level != "-" else place.price_level,
                            'user_ratings_total': place.user_ratings_total,
                            'distance': place.distance, 'vicinity': place.vicinity,
                            'type_of_place': place.type_of_place, 'origin': place.origin, "lat": place.lat, "lng": place.lng} for place in places}
    map_markers = [{"lat": place.lat, "lng": place.lng, "infobox": place.name} for place in places]
    return results, map_markers

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Float)
    price_level = db.Column(db.Integer)
    user_ratings_total = db.Column(db.Integer)
    vicinity = db.Column(db.String(200))
    type_of_place = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    distance = db.Column(db.Float)
    origin = db.Column(db.String(200))

    def __repr__(self):
        return '<Place %r>' % self.name

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=60)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


sort_options = {
    'name': Place.name,
    'rating': Place.rating,
    'price_level': Place.price_level,
    'user_ratings_total': Place.user_ratings_total,
    'vicinity': Place.vicinity,
    'type_of_place': Place.type_of_place,
    'distance': Place.distance
}


with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode("utf-8")

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, password=bcrypt.hashpw(password, salt))
            db.session.add(user)
            db.session.commit()
        else:
            if bcrypt.hashpw(password, user.password) != user.password:
                return render_template('login.html', msg="パスワードを確認してください")

        login_user(user)
        return redirect('/')

    session["prev_loc"] = None
    session["prev_radius"] = None
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/', methods=['POST', 'GET'])
@login_required
def index():
    map_name = "mymap"
    map_markers, map_lat, map_lng = None, None, None
    keyword_list = ["restaurant", "bar", "karaoke"]

    if request.method == 'POST':
        location = request.form['location']
        radius = request.form['radius']
        keywords = request.form.getlist('keyword')
        favs = request.form.getlist('fav')
        session['fav'] = favs

        for keyword in keyword_list:
            if keyword in keywords:
                session[keyword] = True
            else:
                session[keyword] = False

        session["other"] = False

        for keyword in keywords:
            if keyword not in keyword_list:
                session["other"] = keyword

        session["prev_loc"] = location
        session["prev_radius"] = radius



        if location == "" or radius == "" or keywords == [""] or not is_float(radius):
            if not is_float(radius) and not (location == "" or radius == "" or keywords == [""]):
                error = "検索範囲に数字をいれてください"
            else:
                error = "場所、検索範囲またはキーワードを確認してください"

            places = Place.query.filter_by(user_id=current_user.id).all()
            results, map_markers = get_results_and_markers(places)

            return render_template('index.html', results=results,
                                   user=current_user.username, map_name=map_name,
                                   map_lat=map_lat, map_lng=map_lng, map_markers=map_markers,
                                   error=error, prev_loc=location, prev_radius=radius)

        add_japanese(keywords)
        keywords = [x for x in keywords if x != ""]

        scraper = GoogleMapScraper(keywords=keywords, location=location, radius=radius, api_key=GOOGLE_KEY)
        if not scraper.run():
            places = Place.query.filter_by(user_id=current_user.id).all()
            results, map_markers = get_results_and_markers(places)
            return render_template('index.html', results=results,
                                   user=current_user.username, map_name=map_name,
                                   map_lat=map_lat, map_lng=map_lng, map_markers=map_markers,
                                   error="場所がみつかりませんでした", prev_loc=location, prev_radius=radius)

        results = dict(scraper.targets_dict)
        map_lat, map_lng = scraper.lat_lng

        for name, info in results.items():
            change_to_japanese(info)

            place = Place(user_id=current_user.id, name=name, rating=info['rating'], price_level=info['price_level'],
                          user_ratings_total=info['user_ratings_total'], vicinity=info['vicinity'],
                          type_of_place=info['type_of_place'], lat=info["lat"], lng=info["lng"],
                          distance=info["distance"], origin=info["origin"])

            db.session.add(place)
        db.session.commit()

        places = Place.query.filter_by(user_id=current_user.id).all()
        results, map_markers = get_results_and_markers(places)
        return render_template('index.html', results=results, user=current_user.username,
        map_name=map_name, map_lat=map_lat, map_lng=map_lng, map_markers=map_markers, prev_loc=location, prev_radius=radius)
    else:
        places = Place.query.filter_by(user_id=current_user.id).all()
        results, map_markers = get_results_and_markers(places)

        if "prev_loc" not in session:
            session["prev_loc"] = None
            session["prev_radius"] = None

        if len(places) != 0:
            map_lat, map_lng = places[0].lat, places[0].lng
        return render_template('index.html', results=results, user=current_user.username,
        map_name=map_name, map_lat=map_lat, map_lng=map_lng, map_markers=map_markers, prev_loc=session["prev_loc"], prev_radius=session["prev_radius"])

@app.route('/sort', methods=['GET'])
@login_required
def sort():
    map_name = "mymap"
    map_markers, map_lat, map_lng = None, None, None
    column = request.args.get('column', 'name')  # Default to 'name' if no column provided
    session['last_column'] = session.get('last_column', None)
    session['last_direction'] = session.get('last_direction', None)

    if column == session['last_column']:  # If column hasn't changed, toggle direction
        direction = 'desc' if session['last_direction'] == 'asc' else 'asc'
    else:  # If column has changed, default to ascending
        direction = 'asc'
    session['last_column'] = column
    session['last_direction'] = direction
    sort_column = sort_options[column]
    if direction == 'desc':
        places = Place.query.filter_by(user_id=current_user.id).order_by(db.desc(sort_column)).all()
    else:
        places = Place.query.filter_by(user_id=current_user.id).order_by(db.asc(sort_column)).all()

    if len(places) != 0:
        map_markers = [{"lat": place.lat, "lng": place.lng, "infobox": place.name} for place in places]
        map_lat, map_lng = places[0].lat, places[0].lng

    results = {place.name: {'rating': place.rating, 'price_level': place.price_level * "¥" if place.price_level != "-" else place.price_level,
                            'user_ratings_total': place.user_ratings_total, 'distance': place.distance,
                            'vicinity': place.vicinity, 'type_of_place': place.type_of_place,
                            'origin': place.origin,"lat": place.lat, "lng": place.lng} for place in places}

    if "prev_loc" not in session:
            session["prev_loc"] = None
            session["prev_radius"] = None

    return render_template('index.html', results=results, user=current_user.username,
    map_name=map_name, map_lat=map_lat, map_lng=map_lng, map_markers=map_markers, prev_loc=session["prev_loc"], prev_radius=session["prev_radius"], scroll="scroll")


@app.route('/clear', methods=['POST'])
@login_required
def clear_db():
    favs = request.form.getlist('fav')
    session['fav'] = favs
    fav_places = []  # List to store favorited places
    try:
        places = db.session.query(Place).filter(Place.user_id == current_user.id).all()
        for place in places:
            if place.name not in favs:
                db.session.delete(place)
            else:
                fav_places.append(place)
        db.session.commit()
        session['fav_places'] = [place.name for place in fav_places]
        return redirect(url_for('display_fav_places'))
    except Exception as e:
        return str(e)

@app.route('/display_fav_places')
@login_required
def display_fav_places():
    fav_places_names = session.get('fav_places', [])
    fav_places = Place.query.filter(Place.name.in_(fav_places_names)).all()
    results, markers = get_results_and_markers(fav_places)
    map_lat, map_lng = None, None

    if "prev_loc" not in session:
            session["prev_loc"] = None
            session["prev_radius"] = None

    if fav_places:
        map_lat, map_lng = fav_places[0].lat, fav_places[0].lng
    return render_template('index.html', results=results, user=current_user.username,
        map_name="mymap", map_lat=map_lat, map_lng=map_lng, map_markers=markers,
        prev_loc=session["prev_loc"], prev_radius=session["prev_radius"])


@app.route('/delete_user', methods=['GET'])
@login_required
def delete_user():
    try:
        db.session.query(Place).filter(Place.user_id == current_user.id).delete()
        db.session.query(User).filter(User.id == current_user.id).delete()
        db.session.commit()
        logout_user()
        return redirect('/login')
    except Exception as e:
        return str(e)


if __name__ == "__main__":
    app.run(debug=True)