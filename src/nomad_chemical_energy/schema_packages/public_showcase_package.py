#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from baseclasses import BaseMeasurement
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Datetime, Quantity, SchemaPackage, Section, SubSection

m_package = SchemaPackage()

# %% ####################### Entities
# %% ####################### Generic Entries
# %% ####################### Measurements


class EMAR_Showcase(ArchiveSection):
    timestamp = Quantity(
        links=[
            'https://w3id.org/nfdi4cat/voc4cat_0008095',
        ],
        type=np.dtype(np.float64),
        unit=('s'),
        shape=['*'],
        description='Zeitpunkte der pH-Wert-Messungen, angegeben als verstrichene Zeit seit Beginn des EMAR Experiments',
        label='Zeitstempel',
    )

    pH = Quantity(
        links=[
            'http://purl.obolibrary.org/obo/PATO_0001842',
        ],
        type=np.dtype(np.float64),
        shape=['*'],
        description='pH-Wert der Flüssigkeit im EMAR Experiment gemessen in regelmäüigen Abständen über den Zeitraum des Experiments',
    )


class GirlsDay_Laboraufzeichnung(BaseMeasurement, EntryData, PlotSection):
    m_def = Section(
        a_eln=dict(
            hide=[
                'atmosphere',
                'instruments',
                'lab_id',
                'location',
                'method',
                'samples',
                'steps',
                'results',
            ],
            properties=dict(
                order=[
                    'name',
                    'datetime',
                    'operator',
                    'pH',
                    'volume',
                    'temperature',
                    'description',
                    'data_file',
                ]
            ),
        ),
    )

    description = BaseMeasurement.description.m_copy()
    description.label = 'Beschreibung und Notizen'

    datetime = Quantity(
        type=Datetime,
        description='Datum und Uhrzeit, als diese Laboraufzeichnung gestartet wurde.',
        a_eln=dict(component='DateTimeEditQuantity', label='Startzeit'),
    )

    operator = Quantity(
        type=str,
        label='Versuchsleiterin',
        a_eln=dict(
            component='EnumEditQuantity',
            props=dict(
                suggestions=[
                    'Flora Haun',
                    'Carla Terboven',
                ]
            ),
        ),
        description='Name der Person, die die Laboraufzeichnung durchführt.',
    )

    data_file = Quantity(
        type=str,
        a_eln=dict(component='FileEditQuantity'),
        a_browser=dict(adaptor='RawFileAdaptor'),
        description='txt Datei mit den pH-vs-Zeit Messungen für den EMAR Showcase',
        label='EMAR Datei',
    )

    temperature = Quantity(
        links=[
            'http://purl.obolibrary.org/obo/PATO_0000146',
        ],
        type=np.dtype(np.float64),
        unit=('°C'),
        a_eln=dict(component='NumberEditQuantity', defaultDisplayUnit='°C'),
        description='Temperatur der Flüssigkeit',
        label='Temperatur',
    )

    volume = Quantity(
        links=[
            'http://purl.obolibrary.org/obo/PATO_0000918',
        ],
        type=np.dtype(np.float64),
        unit=('mL'),
        a_eln=dict(
            component='NumberEditQuantity',
            defaultDisplayUnit='mL',
            props=dict(minValue=0),
        ),
        description='Volumen der Flüssigkeit',
        label='Volumen',
    )

    pH = Quantity(
        links=[
            'http://purl.obolibrary.org/obo/PATO_0001842',
        ],
        type=np.dtype(np.float64),
        a_eln=dict(
            component='NumberEditQuantity',
            props=dict(minValue=0, maxValue=14),
        ),
        description='pH-Wert der Flüssigkeit',
    )

    emar_showcase = SubSection(section_def=EMAR_Showcase, label='EMAR Beispiel')

    def normalize(self, archive, logger):
        super().normalize(archive, logger)
        if self.data_file:
            if os.path.splitext(self.data_file)[-1] == '.txt':
                with archive.m_context.raw_file(
                    self.data_file,
                    'rt',
                ) as f:
                    f.readline()  # header from first line not needed
                    date_line = f.readline()
                    emar_df = pd.read_csv(f, sep=' ')
                    self.emar_showcase = EMAR_Showcase(
                        pH=emar_df['pH'],
                        timestamp=pd.to_timedelta(
                            emar_df['hh:mm:ss']
                        ).dt.total_seconds(),
                    )
                    temp_match = re.search(r'_(\d+)Deg', self.data_file)
                    if temp_match:
                        self.temperature = int(temp_match.group(1))
                    datetime_match = re.search(r'started\s+(.+)', date_line)
                    if datetime_match:
                        date_str = datetime_match.group(1).strip()
                        self.datetime = datetime.strptime(
                            date_str, '%m/%d/%Y %I:%M:%S %p'
                        )

        if (
            self.emar_showcase
            and self.emar_showcase.timestamp is not None
            and self.emar_showcase.pH is not None
        ):
            plot_title = 'pH über Zeit'
            fig1 = go.Figure(
                data=[
                    go.Scatter(
                        name='pH',
                        x=self.emar_showcase.timestamp,
                        y=self.emar_showcase.pH,
                        mode='lines',
                        hoverinfo='x+y+name',
                    )
                ]
            )
            fig1.update_layout(
                title_text=plot_title,
                xaxis={
                    'fixedrange': False,
                    'title': f'Zeit ({self.emar_showcase.timestamp[0].units:~P})',
                },
                yaxis={
                    'title': 'pH',
                    'fixedrange': False,
                },
                hovermode='closest',
            )
            self.figures = [
                PlotlyFigure(label=plot_title, figure=json.loads(fig1.to_json())),
            ]


m_package.__init_metainfo__()
