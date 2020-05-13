#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json, sys
import dateutil.parser
import babel, logging, time
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import load_only, undefer, defer
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Show(db.Model):
    __tablename__ = 'shows'
    show_id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id', ondelete='CASCADE'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id', ondelete='CASCADE'), nullable=False)
    venue = db.relationship('Venue', backref='shows', lazy=True)
    artist = db.relationship('Artist',backref='shows', lazy=True)
    start_time = db.Column(db.DateTime, nullable=False)

class Venue(db.Model):
    __tablename__ = 'venues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500), default='https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80')
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean(120), default=False)
    seeking_description = db.Column(db.String(120))

class Artist(db.Model):
    __tablename__ = 'artists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    facebook_link = db.Column(db.String(120))
    image_link = db.Column(db.String(500), default='https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80')
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean(120), default=False)
    seeking_description = db.Column(db.String(120))

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format="EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format="EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
   return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    venues_group = Venue.query.distinct(Venue.city, Venue.state).order_by(Venue.state).all()
    shows = Show.query.all()
    venues = Venue.query.all()

    for group in venues_group:
        venues_in_group = [venue for venue in venues if venue.city == group.city and venue.state == group.state]
        for venue in venues_in_group:
            num_upcoming_shows = sum(1 for show in shows if show.venue_id == venue.id and show.start_time > datetime.now())
            venue.num_upcoming_shows = num_upcoming_shows
        data.append({
            'city': group.city,
            'state': group.state,
            'venues': venues_in_group
        })
    return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
    term = request.form['search_term']
    venues = Venue.query.all()
    response = {
        'count': 0,
        'data': []
    }
    shows = Show.query.all()
    for venue in venues:
        if term in venue.name:
            shows_in_future = sum(1 for show in shows if show.venue_id == venue.id and show.start_time > datetime.now())
            response['count'] += 1
            response['data'].append({
                'id': venue.id,
                'name': venue.name,
                'num_upcoming_shows': shows_in_future
            })
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    with db.session.no_autoflush:
        venue = Venue.query.get(venue_id)
        shows = Show.query.filter_by(venue_id=venue_id).all()
        upcoming_shows = []
        past_shows = []
        upcoming_shows_count = 0
        past_shows_count = 0
        for show in shows:
            show.artist_image_link = Artist.query.get(show.artist_id).image_link
            if show.start_time < datetime.now():
                show.start_time = show.start_time.strftime('%Y-/%m-%d/%y %H:%M:%S')
                past_shows_count += 1
                past_shows.append(show)
            else:
                show.start_time = show.start_time.strftime('%Y-/%m-%d/%y %H:%M:%S')
                upcoming_shows_count += 1
                upcoming_shows.append(show)
        venue.past_shows = past_shows
        venue.past_shows_count = past_shows_count
        venue.upcoming_shows = upcoming_shows
        venue.upcoming_shows_count = upcoming_shows_count
        return render_template('pages/show_venue.html', venue=venue)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    req = request.form
    try:
        genres = req.getlist('genres')
        for genre in genres:
            if not any(var.value == genre for var in Genres):
                raise ValueError('Not a genre')
        if not any(var.value == req.get('state') for var in States):
            raise ValueError('Not a State')
        venue = Venue(name=req['name'],
                city=req['city'],
                state=req['state'],
                address=req['address'],
                genres=genres,
                phone=req['phone'],
                facebook_link=req['facebook_link']
        )
        db.session.add(venue)
        db.session.commit()
    except Exception as e:
        print('Error' + str(e))
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + req['name'] + ' could not be listed.')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    error = False
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
    except Exception as e:
        error = True
        print(e)
        db.session.rollback()
        flash('Error occured!')
    finally:
        db.session.close()
    return jsonify({'Success': not error})

#  Artists
#  ----------------------------------------------------------------

@app.route('/artists')
def artists():
    artists = Artist.query.all()
    return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
    term = request.form['search_term']
    artists = Artist.query.all()
    response = {
        'count': 0,
        'data': []
    }
    shows = Show.query.all()
    for artist in artists:
        if term in artist.name:
            shows_in_future = sum(1 for show in shows if show.artist_id == artist.id and show.start_time > datetime.now())
            response['count'] += 1
            response['data'].append({
                'id': artist.id,
                'name': artist.name,
                'num_upcoming_shows': shows_in_future
            })
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    with db.session.no_autoflush:
        artist = Artist.query.get(artist_id)
        shows = Show.query.filter_by(artist_id=artist_id).all()
        upcoming_shows = []
        past_shows = []
        upcoming_shows_count = 0
        past_shows_count = 0
        for show in shows:
            show.venue_image_link = Venue.query.get(show.venue_id).image_link
            if show.start_time < datetime.now():
                show.start_time = show.start_time.strftime('%Y-/%m-%d/%y %H:%M:%S')
                past_shows_count += 1
                past_shows.append(show)
            else:
                show.start_time = show.start_time.strftime('%Y-/%m-%d/%y %H:%M:%S')
                upcoming_shows_count += 1
                upcoming_shows.append(show)
        artist.past_shows = past_shows
        artist.past_shows_count = past_shows_count
        artist.upcoming_shows = upcoming_shows
        artist.upcoming_shows_count = upcoming_shows_count
        return render_template('pages/show_artist.html', artist=artist)

@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    error = False
    try:
        Artist.query.filter_by(id=artist_id).delete()
        db.session.commit()
    except Exception as e:
        error = True
        flash('Error occured!')
        print(e)
        db.session.rollback()
    finally:
        db.session.close()
    return jsonify({'Success': not error})


#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        req = request.form
        genres = req.getlist('genres')
        for genre in genres:
            if not any(var.value == genre for var in Genres):
                raise ValueError('Not a genre')
        artist = Artist.query.get(artist_id)
        artist.name = req['name']
        artist.city = req['city']
        artist.state = req['state']
        artist.genres = genres
        artist.phone = req['phone']
        artist.facebook_link = req['facebook_link']
        db.session.commit()
    except:
        flash('error occures')
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        req = request.form
        genres = req.getlist('genres')
        for genre in genres:
            if not any(var.value == genre for var in Genres):
                raise ValueError('Not a genre')
        venue = Venue.query.get(venue_id)
        venue.name = req['name']
        venue.city = req['city']
        venue.state = req['state']
        venue.address = req['address']
        venue.genres = genres
        venue.phone = req['phone']
        venue.facebook_link = req['facebook_link']
        db.session.commit()
    except:
        flash('error occures')
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    req = request.form
    try:
        genres = req.getlist('genres')
        for genre in genres:
            if not any(var.value == genre for var in Genres):
                raise ValueError('Not a genre')
        if not any(var.value == req.get('state') for var in States):
            raise ValueError('Not a State')
        artist = Artist(name=req['name'],
                city=req['city'],
                state=req['state'],
                genres=genres,
                phone=req['phone'],
                facebook_link=req['facebook_link']
        )
        db.session.add(artist)
        db.session.commit()
    except Exception as e:
        print('Error' + str(e))
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + req['name'] + ' could not be listed.')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    shows = Show.query.all()
    data = [{
        "venue_id": show.venue_id,
        "venue_name": show.venue.name,
        "artist_id": show.artist_id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": show.start_time.strftime('%Y-/%m-%d/%y %H:%M:%S')
    } for show in shows]
    return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    req = request.form
    try:
        show = Show(venue_id=req['venue_id'], artist_id=req['artist_id'], start_time=req['start_time'])
        db.session.add(show)
        db.session.commit()
    except Exception as e:
        print('Error' + str(e))
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
    else:
        flash('Show was successfully listed!')
    return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
