import React, { Component } from 'react';
import GenArt from './GenArt.jsx';
import setupPlotly from './map.js';

import { NamespacesConsumer } from 'react-i18next';

/**
 * A map explore page to explore the latent space of BigGAN
 */
// export default class MapExplorePage extends Component {
class MapExplorePage extends Component {
  constructor(props) {
    super(props);
    this.state = {
      cursorPoint: null,
    };
  }

  componentDidMount() {
    //Decode the url data
    let url = this.props.match.params.id.toString();
    url = decodeURIComponent(url);
    let selectedArt = url.split('&')[0].slice(4);
    let artArr = url.split('&')[1].slice(4);
    artArr = JSON.parse(artArr);

    //Setup the Plotly graph
    setupPlotly(this, artArr, selectedArt);
  }

  render() {
    return (
      <NamespacesConsumer>
        {t => (
          <section className="map">
            <div className="map__header">
              <button className="map__tab is-active">Method 1</button>
              <button className="map__tab">Method 2</button>
            </div>
            <div className="map__content">

              <h1 className="claim">{t('map.title')}</h1>
              <div className="map__data">
                <p className="map__description">{t('map.description')}</p>
                <div className="map__original">
                  test asdasdasdas
                </div>
              </div>

              <div className="map__result">
                <GenArt
                  message={this.state.message}
                  image={this.state.genImg}
                  data={this.state.genArr}
                />

                <div className="plot" id="myPlot" />
              </div>
            </div>
          </section>
        )}
      </NamespacesConsumer>
    );
  }
}

export default MapExplorePage;
