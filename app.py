"""
このFlaskアプリケーションは、ユーザー認証、Googleマップのスクレイピング、および結果のデータベースへの保存を行います。
アプリケーションは以下の機能を提供します：

1. ユーザー認証：Flask-Loginを使用して、ユーザーのログイン、ログアウト、およびセッション管理を行います。
2. Googleマップスクレイピング：ユーザーが提供したキーワード、場所、半径を基にGoogleマップから情報を取得します。
3. データベース操作：SQLAlchemyを使用して、ユーザーとスクレイピング結果をSQLiteデータベースに保存します。
4. ユーザーインターフェース：FlaskとJinja2テンプレートを使用して、ログインページ、検索結果の表示、およびユーザー設定の管理を行うウェブページを提供します。
5. Google Mapsの統合：flask_googlemapsを使用して、検索結果をマップ上にマーカーとして表示します。

アプリケーションは以下の主要なコンポーネントで構成されます：

- Flaskアプリケーション設定：セッションの秘密キーやデータベースの設定など、アプリケーションの基本設定を行います。
- モデル定義：ユーザーと場所のデータモデルを定義し、データベーススキーマを設定します。
- ビュー関数：ログイン、ログアウト、検索結果の表示、データベースの内容変更など、ユーザーからのリクエストに応じた処理を行う関数を定義します。
- ヘルパー関数：データの変換、検索結果の処理、セッション管理など、ビュー関数から呼び出される補助的な機能を提供します。

"""

from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from source.scraper import GoogleMapScraper
from flask_googlemaps import GoogleMaps, Map
import bcrypt
from datetime import timedelta

# Flask appの初期化
app = Flask(__name__)
app.secret_key = 'TeLLMEWHY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

# データベースの初期化
db = SQLAlchemy()
db.init_app(app)

# ログインマネージャの初期化
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Google Maps API キー
GOOGLE_KEY = "AIzaSyDbbDAUExwpzu7IaZ1h_Xw5-i6P2jwtXXs"
GOOGLE_MAP_KEY = "AIzaSyBKOqBE1tCLB4_ruwU8WVyCuDRN0exE_xo"
GoogleMaps(app, key=GOOGLE_MAP_KEY)

# パスワードのハッシュ化のための salt の生成
salt = bcrypt.gensalt()

# 文字列が浮動小数点数に変換可能かどうかをチェックする関数
def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

# キーワードリストに日本語のキーワードを追加する関数、両方英語と日本語の結果が出るため
def add_japanese(keyword_list):
    if "restaurant" in keyword_list:
        keyword_list.insert(0, "飲食店")
    if "bar" in keyword_list:
        keyword_list.insert(0, "バー")
    if "karaoke" in keyword_list:
        keyword_list.insert(0, "カラオケ")

# 情報の種類を日本語に変換する関数
def change_to_japanese(info):
    if info['type_of_place'] == "restaurant":
        info['type_of_place'] = "飲食店"
    if info['type_of_place'] == "bar":
        info['type_of_place'] = "バー"
    if info['type_of_place'] == "karaoke":
        info['type_of_place'] = "カラオケ"

# 検索結果とマップマーカーをデータベースから取得するための関数
def get_results_and_markers(places):
    results = {place.name: {'rating': place.rating, 'price_level': place.price_level * "¥" if place.price_level != "-" else place.price_level,
                            'user_ratings_total': place.user_ratings_total,
                            'distance': place.distance, 'vicinity': place.vicinity,
                            'type_of_place': place.type_of_place, 'origin': place.origin, "lat": place.lat, "lng": place.lng} for place in places}
    map_markers = [{"lat": place.lat, "lng": place.lng, "infobox": place.name} for place in places]
    return results, map_markers

# データベースのUserテーブルを定義する
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# データベースのPlaceテーブルを定義する
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

# アプリケーションコンテキスト内で全データベーステーブルを作成
with app.app_context():
    db.create_all()

# セッションの有効期限を設定
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

# Flask-Loginのユーザーローダー: ユーザーIDからユーザーオブジェクトを取得
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ソートオプションの辞書: ユーザーが選択できるソートオプションを定義
sort_options = {
    'name': Place.name,
    'rating': Place.rating,
    'price_level': Place.price_level,
    'user_ratings_total': Place.user_ratings_total,
    'vicinity': Place.vicinity,
    'type_of_place': Place.type_of_place,
    'distance': Place.distance
}

# ログインページと処理のルートを定義
@app.route('/login', methods=['GET', 'POST']) # /loginに行くと以下のコードが実行される
def login():
    # POSTリクエストの場合、ユーザー認証を実施
    if request.method == 'POST':
        username = request.form['username']  # ユーザー名をフォームから取得
        password = request.form['password'].encode("utf-8")  # パスワードをフォームから取得し、UTF-8でエンコード

        # ユーザー名に基づいてユーザーを検索
        user = User.query.filter_by(username=username).first()
        # ユーザーが存在しない場合、新しいユーザーを作成
        if not user:
            user = User(username=username, password=bcrypt.hashpw(password, salt))
            db.session.add(user)  # 新しいユーザーをデータベースセッションに追加
            db.session.commit()  # データベースに変更をコミット
        else:
            # パスワードが間違っている場合、ログインページにエラーメッセージを表示
            if bcrypt.hashpw(password, user.password) != user.password:
                return render_template('login.html', msg="パスワードを確認してください")

        login_user(user)  # ユーザーをログイン状態にする
        return redirect('/')  # メインページにリダイレクト

    # GETリクエストの場合、またはログインに失敗した場合、ログインページを表示
    session["prev_loc"] = None
    session["prev_radius"] = None
    return render_template('login.html')

# ログアウト処理のルートを定義
@app.route('/logout') # /logoutに行くと以下のコードが実行される
@login_required  # ログインが必要
def logout():
    logout_user()  # ユーザーをログアウト状態にする
    return redirect('/login')  # ログインページにリダイレクト

@app.route('/', methods=['POST', 'GET']) # /に行くと以下のコードが実行される
@login_required
def index():
    map_name = "mymap"
    map_markers, map_lat, map_lng = None, None, None # map_markersはマーカーの位置情報の入っている辞書である
    keyword_list = ["restaurant", "bar", "karaoke"]

    if request.method == 'POST':
        location = request.form['location']
        radius = request.form['radius']
        keywords = request.form.getlist('keyword')
        favs = request.form.getlist('fav')
        session['fav'] = favs

        '''以下のコードはユーザーが以前に入力した設定を覚えるためのものであり、次のコメント分まで無視してよい'''
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
        '''ここまで'''

        # 検索条件が不足している場合、エラーメッセージを表示
        if location == "" or radius == "" or keywords == [""] or not is_float(radius):
            if not is_float(radius) and not (location == "" or radius == "" or keywords == [""]):
                error = "検索範囲に数字をいれてください"
            else:
                error = "場所、検索範囲またはキーワードを確認してください"

            places = Place.query.filter_by(user_id=current_user.id).all()  # ユーザーの全ての場所を取得
            results, map_markers = get_results_and_markers(places)  # 結果とマーカーを取得

            # エラーメッセージと共にメインページを表示
            return render_template('index.html', results=results,
                                   user=current_user.username, map_name=map_name,
                                   map_lat=map_lat, map_lng=map_lng, map_markers=map_markers,
                                   error=error, prev_loc=location, prev_radius=radius)

        # 日本語のキーワードに変換し、空のキーワードを削除
        add_japanese(keywords)
        keywords = [x for x in keywords if x != ""]

        # GoogleMapScraperを使用して検索を実行
        scraper = GoogleMapScraper(keywords=keywords, location=location, radius=radius, api_key=GOOGLE_KEY)
        if not scraper.run():
            places = Place.query.filter_by(user_id=current_user.id).all()  # ユーザーの全ての場所を取得
            results, map_markers = get_results_and_markers(places)  # 結果とマーカーを取得
            # 検索に失敗した場合、エラーメッセージと共にメインページを表示
            return render_template('index.html', results=results,
                                   user=current_user.username, map_name=map_name,
                                   map_lat=map_lat, map_lng=map_lng, map_markers=map_markers,
                                   error="場所がみつかりませんでした", prev_loc=location, prev_radius=radius)

        results = dict(scraper.targets_dict)  # 検索結果を辞書に変換
        map_lat, map_lng = scraper.lat_lng  # マップの緯度と経度を取得

        # 検索結果をデータベースに保存
        for name, info in results.items():
            change_to_japanese(info)  # 情報を日本語に変換

            place = Place(user_id=current_user.id, name=name, rating=info['rating'], price_level=info['price_level'],
                          user_ratings_total=info['user_ratings_total'], vicinity=info['vicinity'],
                          type_of_place=info['type_of_place'], lat=info["lat"], lng=info["lng"],
                          distance=info["distance"], origin=info["origin"])

            db.session.add(place)  # 場所をデータベースセッションに追加
        db.session.commit()  # データベースに変更をコミット

        places = Place.query.filter_by(user_id=current_user.id).all()  # ユーザーの全ての場所を取得
        results, map_markers = get_results_and_markers(places)  # 結果とマーカーを取得
        # メインページを表示
        return render_template('index.html', results=results, user=current_user.username,
                               map_name=map_name, map_lat=map_lat, map_lng=map_lng, map_markers=map_markers,
                               prev_loc=location, prev_radius=radius)
    else:
        # GETリクエストの場合、ユーザーの全ての場所を取得し、メインページを表示
        places = Place.query.filter_by(user_id=current_user.id).all()
        results, map_markers = get_results_and_markers(places)

        if "prev_loc" not in session:
            session["prev_loc"] = None
            session["prev_radius"] = None

        if len(places) != 0:
            map_lat, map_lng = places[0].lat, places[0].lng
        return render_template('index.html', results=results, user=current_user.username,
                               map_name=map_name, map_lat=map_lat, map_lng=map_lng, map_markers=map_markers,
                               prev_loc=session["prev_loc"], prev_radius=session["prev_radius"])

@app.route('/sort', methods=['GET']) # /sortに行くと以下のコードが実行される
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


@app.route('/clear', methods=['POST']) # /clearに行くと以下のコードが実行される
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

@app.route('/display_fav_places') # /display_fav_placesに行くと以下のコードが実行される
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


@app.route('/delete_user', methods=['GET']) # /delete_userに行くと以下のコードが実行される
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