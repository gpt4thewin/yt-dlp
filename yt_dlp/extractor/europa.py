import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    traverse_obj,
    unified_strdate,
    xpath_text,
    update_url_query,
    datetime_from_str
)


def _parse_datetime(datetime_str):
    datetime_format_with_microseconds = "%Y-%m-%dT%H:%M:%S.%f%z"
    datetime_format_without_microseconds = "%Y-%m-%dT%H:%M:%S%z"

    datetime_regex_with_microseconds = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,7}[+-]\d{2}:\d{2}"
    datetime_regex_without_microseconds = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}"

    if re.match(datetime_regex_with_microseconds, datetime_str):
        try:
            pattern = r"(\.\d{6})\d*"
            datetime_str = re.sub(pattern, r"\1", datetime_str)
            return datetime_from_str(datetime_str, format=datetime_format_with_microseconds)
        except ValueError:
            pass

    if re.match(datetime_regex_without_microseconds, datetime_str):
        try:
            return datetime_from_str(datetime_str, format=datetime_format_without_microseconds)
        except ValueError:
            pass

    # If both attempts failed, return None
    return None


class EuropaIE(InfoExtractor):
    _VALID_URL = r'https?://ec\.europa\.eu/avservices/(?:video/player|audio/audioDetails)\.cfm\?.*?\bref=(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?ref=I107758',
        'md5': '574f080699ddd1e19a675b0ddf010371',
        'info_dict': {
            'id': 'I107758',
            'ext': 'mp4',
            'title': 'TRADE - Wikileaks on TTIP',
            'description': 'NEW  LIVE EC Midday press briefing of 11/08/2015',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150811',
            'duration': 34,
            'view_count': int,
            'formats': 'mincount:3',
        }
    }, {
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?sitelang=en&ref=I107786',
        'only_matching': True,
    }, {
        'url': 'http://ec.europa.eu/avservices/audio/audioDetails.cfm?ref=I-109295&sitelang=en',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        playlist = self._download_xml(
            'http://ec.europa.eu/avservices/video/player/playlist.cfm?ID=%s' % video_id, video_id)

        def get_item(type_, preference):
            items = {}
            for item in playlist.findall('./info/%s/item' % type_):
                lang, label = xpath_text(item, 'lg', default=None), xpath_text(item, 'label', default=None)
                if lang and label:
                    items[lang] = label.strip()
            for p in preference:
                if items.get(p):
                    return items[p]

        query = parse_qs(url)
        preferred_lang = query.get('sitelang', ('en', ))[0]

        preferred_langs = orderedSet((preferred_lang, 'en', 'int'))

        title = get_item('title', preferred_langs) or video_id
        description = get_item('description', preferred_langs)
        thumbnail = xpath_text(playlist, './info/thumburl', 'thumbnail')
        upload_date = unified_strdate(xpath_text(playlist, './info/date', 'upload date'))
        duration = parse_duration(xpath_text(playlist, './info/duration', 'duration'))
        view_count = int_or_none(xpath_text(playlist, './info/views', 'views'))

        language_preference = qualities(preferred_langs[::-1])

        formats = []
        for file_ in playlist.findall('./files/file'):
            video_url = xpath_text(file_, './url')
            if not video_url:
                continue
            lang = xpath_text(file_, './lg')
            formats.append({
                'url': video_url,
                'format_id': lang,
                'format_note': xpath_text(file_, './lglabel'),
                'language_preference': language_preference(lang)
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'formats': formats
        }


class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://multimedia\.europarl\.europa\.eu/[^/#?]+/
        (?:(?!video)[^/#?]+/[\w-]+_)(?P<id>[\w-]+)
    '''
    _TESTS = [{
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': '62388b15-d85b-4add-99aa-ba12ccf64f0d',
            'ext': 'mp4',
            'title': 'Plenary session',
            'release_timestamp': 1663139069,
            'release_date': '20220914',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # live webstream
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20221115-1000-SPECIAL-EUROSCOLA',
        'info_dict': {
            'ext': 'mp4',
            'id': '510eda7f-ba72-161b-7ee7-0e836cd2e715',
            'release_timestamp': 1668502800,
            'title': 'Euroscola 2022-11-15 19:21',
            'release_date': '20221115',
            'live_status': 'is_live',
        },
        'skip': 'not live anymore'
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-culture-and-education_20230301-1130-COMMITTEE-CULT',
        'info_dict': {
            'id': '7355662c-8eac-445e-4bb9-08db14b0ddd7',
            'ext': 'mp4',
            'release_date': '20230301',
            'title': 'Committee on Culture and Education',
            'release_timestamp': 1677666641,
        }
    }, {
        # live stream
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-environment-public-health-and-food-safety_20230524-0900-COMMITTEE-ENVI',
        'info_dict': {
            'id': 'e4255f56-10aa-4b3c-6530-08db56d5b0d9',
            'ext': 'mp4',
            'release_date': '20230524',
            'title': r're:Committee on Environment, Public Health and Food Safety \d{4}-\d{2}-\d{2}\s\d{2}:\d{2}',
            'release_timestamp': 1684911541,
            'live_status': 'is_live',
        },
        'skip': 'Not live anymore'
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        webpage_nextjs = self._search_nextjs_data(webpage, display_id)['props']['pageProps']

        json_info = self._download_json(
            'https://acs-api.europarl.connectedviews.eu/api/FullMeeting', display_id,
            query={
                'api-version': 1.0,
                'tenantId': 'bae646ca-1fc8-4363-80ba-2c04f06b4968',
                'externalReference': display_id
            })

        # TODO: Secure for live
        start_actual = _parse_datetime(traverse_obj(json_info, 'startDateTime'))
        end_actual = _parse_datetime(traverse_obj(json_info, 'endDateTime'))
        video_duration = (end_actual - start_actual).total_seconds().__floor__()

        def _get_lang(track_identifier):
            if track_identifier is None:
                return None
            for audio in json_info.get('meetingAudio', []):
                if audio.get('trackIdentifier') == track_identifier:
                    return audio.get('language')
            return None

        formats, subtitles = [], {}
        for hls_url in traverse_obj(json_info, ((('meetingVideo'), ('meetingVideos', ...)), 'hlsUrl')):
            hls_url = update_url_query(hls_url, {'start': start_actual.strftime('%Y-%m-%dT%H:%M:%SZ'), 'end': end_actual.strftime('%Y-%m-%dT%H:%M:%SZ')})
            fmt, subs = self._extract_m3u8_formats_and_subtitles(hls_url, display_id)
            formats.extend(fmt)
            for elem in fmt:
                elem['language'] = _get_lang(elem.get('language'))
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': json_info['id'],
            'title': traverse_obj(webpage_nextjs, (('mediaItem', 'title'), ('title', )), get_all=False),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': parse_iso8601(json_info.get('startDateTime')),
            'is_live': traverse_obj(webpage_nextjs, ('mediaItem', 'mediaSubType')) == 'Live',
            'duration': video_duration,
        }


class EuroParlWebstreamIE2(InfoExtractor):
    # https://multimedia.europarl.europa.eu/fr/video/press-conference-by-roberta-metsola-ep-president-juan-fernando-lopez-aguilar-es-sd-tomas-tobe-se-epp-and-fabienne-keller-fr-renew-rapporteurs-on-the-outcome-of-the-migration-trilogue_I251079
    #
    _VALID_URL = r'''(?x)
        https?://multimedia\.europarl\.europa\.eu/[a-z]{2}/
        (?:video)([\w-]+)
    '''
    # _tests = [{
    #     'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-plenary',
    #     'info_dict': {
    #         'id': '62388b15-d85b-4add-99aa-ba12ccf64f0d',
    #         'ext': 'mp4',
    #         'title': 'plenary session',
    #         'release_timestamp': 1663139069,
    #         'release_date': '20220914',
    #     },
    #     'params': {
    #         'skip_download': true,
    #     }
    # }, {
    #     # live webstream
    #     'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20221115-1000-special-euroscola',
    #     'info_dict': {
    #         'ext': 'mp4',
    #         'id': '510eda7f-ba72-161b-7ee7-0e836cd2e715',
    #         'release_timestamp': 1668502800,
    #         'title': 'euroscola 2022-11-15 19:21',
    #         'release_date': '20221115',
    #         'live_status': 'is_live',
    #     },
    #     'skip': 'not live anymore'
    # }, {
    #     'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-culture-and-education_20230301-1130-committee-cult',
    #     'info_dict': {
    #         'id': '7355662c-8eac-445e-4bb9-08db14b0ddd7',
    #         'ext': 'mp4',
    #         'release_date': '20230301',
    #         'title': 'committee on culture and education',
    #         'release_timestamp': 1677666641,
    #     }
    # }, {
    #     # live stream
    #     'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-environment-public-health-and-food-safety_20230524-0900-committee-envi',
    #     'info_dict': {
    #         'id': 'e4255f56-10aa-4b3c-6530-08db56d5b0d9',
    #         'ext': 'mp4',
    #         'release_date': '20230524',
    #         'title': r're:committee on environment, public health and food safety \d{4}-\d{2}-\d{2}\s\d{2}:\d{2}',
    #         'release_timestamp': 1684911541,
    #         'live_status': 'is_live',
    #     },
    #     'skip': 'not live anymore'
    # }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        webpage_nextjs = self._search_nextjs_data(webpage, display_id)['props']['pageProps']
        entity_id = webpage_nextjs['entryId']
        formats = webpage_nextjs['mediaItem']['videos']['resolutions'] # array: bitRate, format, resolution, size, url
        subtitles = webpage_nextjs['mediaItemV2']['mediaAssets'] # array: label="transcript", textLang, url

        # props.pageProps.mediaItemV2.mediaAssets[0]
        # subtitles (embeded in json): props.pageProps.subtitles
        # props.pageProps.mediaItemV2.duration
        # props.pageProps.mediaItemV2.publicationStartDate
        # props.pageProps.mediaItemV2.mediaDate

        json_info = self._download_json(
            'https://acs-api.europarl.connectedviews.eu/api/FullMeeting', display_id,
            query={
                'api-version': 1.0,
                'tenantId': 'bae646ca-1fc8-4363-80ba-2c04f06b4968',
                'externalReference': display_id
            })

        # TODO: Secure for live
        start_actual = _parse_datetime(traverse_obj(json_info, 'startDateTime'))
        end_actual = _parse_datetime(traverse_obj(json_info, 'endDateTime'))
        video_duration = (end_actual - start_actual).total_seconds().__floor__()

        def _get_lang(track_identifier):
            if track_identifier is None:
                return None
            for audio in json_info.get('meetingAudio', []):
                if audio.get('trackIdentifier') == track_identifier:
                    return audio.get('language')
            return None

        formats, subtitles = [], {}
        for hls_url in traverse_obj(json_info, ((('meetingVideo'), ('meetingVideos', ...)), 'hlsUrl')):
            #hls_url = update_url_query(hls_url, {'start': start_actual.strftime('%Y-%m-%dT%H:%M:%SZ'), 'end': end_actual.strftime('%Y-%m-%dT%H:%M:%SZ')})
            #fmt, subs = self._extract_m3u8_formats_and_subtitles(hls_url, display_id)
            formats.extend(fmt)
            for elem in fmt:
                elem['language'] = _get_lang(elem.get('language'))
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': json_info['id'],
            'title': traverse_obj(webpage_nextjs, (('mediaItem', 'title'), ('title', )), get_all=False),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': parse_iso8601(json_info.get('startDateTime')),
            'is_live': traverse_obj(webpage_nextjs, ('mediaItem', 'mediaSubType')) == 'Live',
            'duration': video_duration,
        }
