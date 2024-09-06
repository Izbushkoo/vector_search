import asyncio
import copy
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Union
from pydantic import BaseModel
from striprtf.striprtf import rtf_to_text


class MatchPattern(BaseModel):
    key: str
    start: int
    finish: int


class CustomInterpretationParser:
    """Даты возвращает объектами а не строками"""

    def __init__(self):
        self._separator_keys = {
            "ID informacji:": "id",
            "Kategoria informacji:": "information_category",
            "Status informacji:": "information_status",
            "Tytuł \(teza\):": "title",
            "Autor informacji:": "author",
            "Data publikacji:": "publication_date",
            "Data wydania:": "release_date",
            "Sygnatura:": "signature",
            "Informacja zmieniana:": "modified_information",
            "Komentarz BIP:": "bip_comment",
            "Opis do komentarza BIP:": "description_bip_comment",
            "Słowa kluczowe:": "keywords",
            "Przepis:": "directive",
            "Zagadnienie:": "issue",
            "Załączniki:": "attachments",
            "Treść:": "content",
            "Treść interpelacji/zapytania:": "content"
        }

    def get_separtor_keys(self):
        return list(set(self._separator_keys.values()))

    @classmethod
    def read_file(cls, path) -> str:
        with open(path, 'r') as file:
            return file.read()

    @classmethod
    def read_from_rtf(cls, path):
        rtf_content = cls.read_file(path)
        text_content = rtf_to_text(rtf_content, encoding="utf-8")
        return text_content.replace("|", "\n")

    def create_from_file_with_keys(self, file_path: str, keys: Union[List[str], str]):
        # text = self.read_file(file_path)
        text = self.read_from_rtf(file_path)
        return self.withdraw_by_key(keys, text)

    def create_from_file_for_postgres(self, file_path: str):
        text = self.read_file(file_path)
        return self.withdraw_postgres_metadata(text)

    def create_metadata_v2(self, text):

        matches_list = []
        for separator_pol, separator_eng in self._separator_keys.items():
            match = re.search(separator_pol, text)
            try:
                span = match.span()
            except AttributeError:
                pass
            else:
                matches_list.append(
                    MatchPattern(
                        key=separator_eng,
                        start=span[0],
                        finish=span[1]
                    )
                )

        starts_hash_pointer, finishes_hash_pointer = {}, {}
        starts, finishes = [], []

        for match_obj in matches_list:
            starts.append(match_obj.start)
            starts_hash_pointer[match_obj.start] = match_obj
            finishes.append(match_obj.finish)
            finishes_hash_pointer[match_obj.finish] = match_obj

        starts, finishes = sorted(starts), sorted(finishes)
        metadata = {}

        for index, start_1 in enumerate(starts):
            try:
                start_2 = starts[index + 1]
            except IndexError:
                start_2 = len(text) + 1

            finish_1 = None
            for finish in finishes:
                if start_1 < finish < start_2:
                    finish_1 = finish
                    break
            start_1_hash_point: MatchPattern = starts_hash_pointer[start_1]
            finish_1_hash_point: MatchPattern = finishes_hash_pointer[finish_1]
            if start_1_hash_point is finish_1_hash_point:
                part_text = text[finish_1:start_2]
                metadata[start_1_hash_point.key] = part_text

        return self._split_metadata(metadata)

    @classmethod
    def _create_approved_tag(cls, content: str):

        pattern = r"INTERPRETACJA INDYWIDUALNA.*?UZASADNIENIE"
        matches = re.search(pattern, content, re.DOTALL)
        approved = []

        if matches:
            modified_content = re.sub(pattern, '', content, flags=re.DOTALL)
            approved.append(matches[0])
            return approved, modified_content
        else:
            pattern = r'Interpretacja indywidualna.*?Treść wniosku jest następująca:'
            matches = re.search(pattern, content, re.DOTALL)
            if matches:
                modified_content = re.sub(pattern, '', content, flags=re.DOTALL)
                approved.append(matches[0])
                return approved, modified_content
            else:
                return approved, content

    @classmethod
    def _split_metadata(cls, metadata: Dict):
        new_metadata = dict()

        for key, value in metadata.items():
            if key == 'content':
                approved, new_content = cls._create_approved_tag(value)
                new_metadata["approved"] = approved
                new_metadata["content"] = new_content
                continue
            new_value = re.sub(r"\n+", "", value).split('    • ')
            if isinstance(new_value, List):
                if key == 'author':
                    value = "\n".join(value)
                else:
                    value = [item for item in new_value if item != '']
            if len(value) == 1 and key != 'directives':
                value = value[0]
            if key in ("publication_date", "release_date"):
                FORMAT_DATE = "%Y-%m-%d"
                FORMAT_TIMESTAMP = "%Y-%m-%dT%H:%M:%S.%fZ"
                try:
                    dt_object = datetime.strptime(value, FORMAT_DATE)
                except ValueError:
                    dt_object = datetime.strptime(value, FORMAT_TIMESTAMP)
                except TypeError:
                    res = re.search("Tytuł \(teza\):", value[0])
                    value = value[0][:res.span()[0]]
                    dt_object = datetime.strptime(value, FORMAT_TIMESTAMP)
                value = dt_object
            new_metadata[key] = value
        return new_metadata

    def withdraw_postgres_metadata(self, text: str):
        all_metadata = self.create_metadata_v2(text)
        valuable_metadata_dict = {}
        for key in ['id', 'author', 'title', 'signature', "keywords", "approved", "release_date", "content"]:
            value = all_metadata.get(key)
            if isinstance(value, (Dict, List)):
                valuable_metadata_dict[key] = copy.deepcopy(value)
            elif value is None:
                pass
            else:
                valuable_metadata_dict[key] = value
        valuable_metadata_dict['id'] = str(valuable_metadata_dict['id'])
        return valuable_metadata_dict

    def withdraw_by_key(self, key: Union[str, List[str]], text: str):
        metadata = self.create_metadata_v2(text)
        if isinstance(key, List):
            if not all([isinstance(elem, str) for elem in key]):
                raise ValueError(f"All the passed items must be a string")
            else:
                key = [k for k in key if k in [*self._separator_keys.values(), "approved"]]
                result_dict = dict()
                for k in key:
                    try:
                        if k == "id":
                            result_dict[k] = int(metadata[k])
                        else:
                            result_dict[k] = metadata[k]
                    except KeyError:
                        pass
                return result_dict

        elif isinstance(key, str):
            if key not in [*self._separator_keys.values(), "approved"]:
                raise KeyError(f"Allowable keys: {self._separator_keys.values()}")
            return {key: metadata[key]}
        else:
            raise ValueError

