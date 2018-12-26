#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Tests for the Narrative class.
"""

from collections import Counter
import unittest
import numpy as np
import pandas as pd
from nlg import Narrative as N

np.random.seed(1234)


class TestNarrative(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        df = pd.read_csv('data/assembly.csv')
        df['vote_share'] = df.pop(
            'Vote share').apply(lambda x: x.replace('%', '')).astype(int)
        cls.df = df

    def test_simple_tmpl(self):
        """Check if simple templating works."""
        self.assertEqual(N('hello world').render(), 'hello world')
        self.assertEqual(N('Hello {name}', name='gramener').render(),
                         'Hello gramener')
        self.assertEqual(N('hello {name[0]}', name=['world', 'hello']).render(),
                         'hello world')
        self.assertEqual(N('hello {x.imag:.0f}', x=(1 + 1j * 42)).render(), 'hello 42')
        self.assertEqual(N().render(), '')

    def test_random_template(self):
        """Check if picking a random template works."""
        choices = [
            '{project} was what you spent most of your time in week {week}, {name}.',
            '{name}, in week {week}, you spent most of your time in {project}',
            'Week {week}: your top project was {project}']
        n = N(choices, name='Anand', week=49, project='Dell')
        self.assertIn(n.render(), [c.format(**n.fmt_kwargs) for c in choices])
        choices = [
            '{project} was what you spent most of your time in week {week}, {name}.',
            '{name}, in week {week}, you spent most of your time in {project}',
            'Week {week}: your top project was {project}']
        op = []
        weights = [0.5, 0.25, 0.25]
        for i in range(50):
            n = N(choices, tmpl_weights=weights,
                  name='Anand', week=49, project='Dell')
            op.append(n.render())
        counts = [c for _, c in Counter(op).most_common()]
        self.assertListEqual(counts, [21, 16, 13])

    def test_data_ref(self):
        """Test if the template can refer to a dataframe."""
        tmpl = """
        BJP won a voteshare of {x}% in {y}, followed by {a}% in {b} and
        {c}% in {d}."""
        n = N(tmpl, data=self.df,
              x='{data.vote_share[0]}', y='{data.AC[0]}',
              a='{data.vote_share[1]}', b='{data.AC[1]}',
              c='{data.vote_share[2]}', d='{data.AC[2]}')
        ideal = tmpl.format(x=24, y='Jaisalmer', a=22, b='Jaipur', c=20,
                            d='Jodhpur')
        self.assertEqual(n.render(), ideal)

    def test_extreme_templates(self):
        """test_extreme_templates"""
        struct = {
            'intent': 'extreme',
            'data': self.df,
            'metadata': {
                'subject': 'BJP',
                'verb': ['won', 'scored', 'achieved'],
                'adjective': ['highest', 'greatest', 'most', 'largest'],
                'object': {
                    'template': 'vote share of {value}% in {location}',
                    'location': {
                        '_type': 'cell',
                        'colname': 'AC',
                        '_filter': {'colname': 'vote_share', 'filter': 'max'}
                    },
                    'value': {
                        '_type': 'cell',
                        'colname': 'vote_share',
                        '_filter': 'max'
                    }
                }
            }
        }
        ideal = 'BJP ({verbs}) the ({adjs}) vote share of 24% in Jaisalmer'
        self.assertRegex(N(struct=struct).render(),
                         ideal.format(
                             verbs='|'.join(struct['metadata']['verb']),
                             adjs='|'.join(struct['metadata']['adjective'])))

    def test_filter_expressions(self):
        """test_filter_expressions"""
        struct = {
           'intent': 'extreme',
           'data': self.df,
           'metadata': {
               'subject': 'BJP',
               'verb': ['won', 'scored', 'achieved'],
               'adjective': ['highest', 'greatest', 'most', 'largest'],
               'object': {
                   'template': 'vote share of {value}% in {location}',
                   'location': {
                       '_type': 'cell',
                       'colname': 'AC',
                       '_filter': 'max(vote_share)'  # filter expression
                   },
                   'value': {
                       '_type': 'cell',
                       'colname': 'vote_share',
                       '_filter': 'max'
                   }
               }
           }
        }
        ideal = 'BJP ({verbs}) the ({adjs}) vote share of 24% in Jaisalmer'
        self.assertRegex(N(struct=struct).render(),
                         ideal.format(
                             verbs='|'.join(struct['metadata']['verb']),
                             adjs='|'.join(struct['metadata']['adjective'])))

    def test_non_literal_pos(self):
        """test_non_literal_pos"""
        df = pd.DataFrame.from_dict({
            'singer': ['Kishore', 'Kishore', 'Kishore'],
            'partner': ['Lata', 'Asha', 'Rafi'],
            'n_songs': [20, 5, 15]
        })

        struct = {
            'intent': 'extreme',
            'data': df,
            'metadata': {
                'subject': {  # non-literal subject
                    '_type': 'cell',
                    'colname': 'singer',
                    '_filter': 'mode'
                },
                'verb': 'sang',
                'adjective': 'most',
                'object': {
                    'template': 'duets with {partner}',
                    'partner': {
                        '_type': 'cell',
                        'colname': 'partner',
                        '_filter': {'colname': 'n_songs', 'filter': 'max'}
                    }
                }
            }
        }
        self.assertEqual(N(struct=struct).render(),
                         'Kishore sang the most duets with Lata.')

    def test_comparison_template(self):
        """test_comparison_template"""
        df = pd.DataFrame.from_dict({
            'character': ['Ned Stark', 'Jon Snow'],
            'n_episodes': [10, 56],
            'time_per_episode': [6.2, 5.5]
        })
        struct = {
            'intent': 'comparison',
            'data': df,
            'metadata': {
                'subject': {
                    'template': '{character}\'s screen time per episode',
                    'character': {
                        '_type': 'cell',
                        'colname': 'character',
                        '_filter': 'max(time_per_episode)'
                    }
                },
                'verb': 'is',
                'quant': {
                    'template': '{q} minutes',
                    'q': {
                        '_type': 'operation',
                        'expr': '{data.iloc[0].time_per_episode} - {data.iloc[1].time_per_episode}'
                    }
                },
                'adjective': 'more',
                'object': {
                    'template': 'that of {character}',
                    'character': {
                        '_type': 'cell',
                        'colname': 'character',
                        '_filter': 'min(time_per_episode)'
                    }
                }
            }
        }
        self.assertRegex(
            N(struct=struct).render(),
            'Ned Stark\'s screen time per episode is 0.7\d+ minutes more than that of Jon Snow\.'
        )
        struct = {
            'intent': 'comparison',
            'data': self.df,
            'metadata': {
                'subject': {
                    'template': '{party}\'s voteshare',
                    'kwargs': {
                        'party': {
                            '_type': 'cell',
                            'colname': 'Party',
                            '_filter': 'mode'
                        }
                    }
                },
                'verb': 'is',
                'quant': {
                    'template': '{q}%',
                    'kwargs': {
                        'q': {
                            '_type': 'operation',
                            'expr': '{data.iloc[0].vote_share}-{data.iloc[2].vote_share}'
                        }
                    }
                },
                'adjective': ['higher', 'greater', 'more'],
                'object': {
                    'template': 'in {x} than in {y}',
                    'kwargs': {
                        'x': {
                            '_type': 'cell',
                            'colname': 'AC',
                            '_filter': 'max(vote_share)'
                        },
                        'y': {
                            '_type': 'cell',
                            'colname': 'AC',
                            '_filter': 'min(vote_share)'
                        }
                    }
                }
            }
        }
        self.assertRegex(
            N(struct=struct).render(),
            'BJP\'s voteshare is 4% (higher|greater|more) than in Jaisalmer than in Jodhpur\.'
        )
