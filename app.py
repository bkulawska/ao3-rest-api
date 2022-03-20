import os
import aiohttp
import asyncio
from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


app = Flask(__name__)
app.config['SECRET_KEY'] = 'C2HWGVoMGfNTBsrYQg8EfAb'
Bootstrap(app)


async def ask_image_external_api(tag, session):
    bing_url = "https://bing-image-search1.p.rapidapi.com/images/search?q=" + tag
    headers = {
        'x-rapidapi-host': "bing-image-search1.p.rapidapi.com",
        'x-rapidapi-key': "2f53c04e38msh7d8017281ad03a0p1c00d0jsn00a7f9711a23"
    }
    async with session.get(bing_url, headers=headers) as bing_response:
        if bing_response.status != 200:
            raise Exception("Bing image search external server did not respond correctly")
        data = await bing_response.json()
        if not data['value']:
            return None
        photo_url = data['value'][0]['thumbnailUrl']
        return photo_url


async def ask_ao3_external_api(tag, session):
    ao3_url = "https://fandomstats.org/api/v1.0/stats?tag_id=" + tag
    async with session.get(ao3_url) as ao3_response:
        if ao3_response.status != 200:
            raise Exception("AO3 external server did not respond correctly")
        data = await ao3_response.json()
        numworks = data['numworks']
        return numworks


async def ask_ao3_and_moviedb_external_api(first_tag, second_tag, session):
    ao3_url = "https://fandomstats.org/api/v1.0/stats?tag_id=" + first_tag + "&other_tag_names[]=" + second_tag
    async with session.get(ao3_url) as ao3_response:
        if ao3_response.status != 200:
            raise Exception("AO3 external server did not respond correctly")
        ao3_data = await ao3_response.json()
        numworks = ao3_data['numworks']
        stats = ao3_data['stats']
        if not stats['character']:
            character = "none"
        else:
            character = list(stats['character'].keys())[0]
        if not stats['relationship']:
            relationship = "none"
        else:
            relationship = list(stats['relationship'].keys())[0]
        if not stats['fandom']:
            fandom = "Sorry, no fandom was found for those tags combined."
            fandom_plot = "none"
            return numworks, fandom, fandom_plot, character, relationship
        else:
            fandom = list(stats['fandom'].keys())[0].split('-')[0]
            id_url = "https://online-movie-database.p.rapidapi.com/title/find?q=" + fandom
            headers = {
                'x-rapidapi-host': "online-movie-database.p.rapidapi.com",
                'x-rapidapi-key': "2f53c04e38msh7d8017281ad03a0p1c00d0jsn00a7f9711a23"
            }
            async with session.get(id_url, headers=headers) as id_response:
                if id_response.status != 200:
                    raise Exception("MovieDB external server did not respond correctly")
                id_data = await id_response.json()
                if not id_data['results']:
                    fandom_plot = "Sorry, the fandom was not found in the database."
                    return numworks, fandom, fandom_plot, character, relationship
                else:
                    fandom_id = id_data['results'][0]['id']
                    fandom_id_clean = fandom_id.split('/')[2]
                    plot_url = "https://online-movie-database.p.rapidapi.com/title/get-plots?tconst=" + fandom_id_clean
                    async with session.get(plot_url, headers=headers) as plot_response:
                        if plot_response.status != 200:
                            raise Exception("MovieDB external server did not respond correctly")
                        plot_data = await plot_response.json()
                        if not plot_data['plots']:
                            fandom_plot = "Sorry, description of the fandom was not found in the database."
                        else:
                            fandom_plot = plot_data['plots'][0]['text']
                        return numworks, fandom, fandom_plot, character, relationship


async def do_some_logic(first_tag, second_tag):
    async with aiohttp.ClientSession() as session:
        first_tag_ao3_search = asyncio.ensure_future(ask_ao3_external_api(first_tag, session))
        second_tag_ao3_search = asyncio.ensure_future(ask_ao3_external_api(second_tag, session))
        both_tags_ao3_moviedb_search = \
            asyncio.ensure_future(ask_ao3_and_moviedb_external_api(first_tag, second_tag, session))
        first_tag_image_search = asyncio.ensure_future(ask_image_external_api(first_tag, session))
        second_tag_image_search = asyncio.ensure_future(ask_image_external_api(second_tag, session))

        first_numworks, second_numworks, res, first_photo_url, second_photo_url = \
            await asyncio.gather(first_tag_ao3_search, second_tag_ao3_search, both_tags_ao3_moviedb_search,
                                 first_tag_image_search, second_tag_image_search)

        diff = abs(first_numworks - second_numworks)
        if first_numworks > second_numworks:
            winner = first_tag
        else:
            winner = second_tag

        return first_numworks, second_numworks, diff, winner, res[0], res[1], res[2], res[3], res[4], first_photo_url,\
               second_photo_url


class NameForm(FlaskForm):
    first_tag = StringField('Enter the first tag:', validators=[DataRequired()])
    second_tag = StringField('Enter the second tag:', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.is_submitted():
        first_tag = form.first_tag.data
        second_tag = form.second_tag.data
        return redirect(url_for('results', first_tag=first_tag, second_tag=second_tag))
    return render_template('index.html', form=form)


@app.route('/results/<first_tag>/<second_tag>')
async def results(first_tag, second_tag):
    first_numworks, second_numworks, diff, winner, both_numworks, fandom, fandom_plot, character, relationship,\
    first_photo_url, second_photo_url = await do_some_logic(first_tag, second_tag)

    return render_template('results.html', first_tag=first_tag, second_tag=second_tag, first_photo=first_photo_url,
                           second_photo=second_photo_url, fandom=fandom, fandom_plot=fandom_plot,
                           character=character, relationship=relationship, first_numworks=first_numworks,
                           second_numworks=second_numworks, both_numworks=both_numworks, diff=diff, winner=winner)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message='Page not found (Error 404)'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', message='Internal server error (Error 500)'), 500


@app.errorhandler(Exception)
def external_server_error(e):
    return render_template('error.html', message=str(e))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
