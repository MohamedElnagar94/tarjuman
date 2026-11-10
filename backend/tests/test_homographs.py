from tarjuman.voice.homographs import disambiguate


def test_the_english_decides_how_an_ambiguous_word_is_said():
    src = "sentences now let's delve into the selection process"
    assert disambiguate("الجمل الآن دعونا نتعمق في عملية الاختيار", src) == "الجُمَل الآن دعونا نتعمق في عملية الاختيار"
    assert disambiguate("رأينا الجمل في الصحراء", "we saw the camel in the desert") == "رأينا الجَمَل في الصحراء"


def test_prefixes_are_kept_and_longer_words_are_left_alone():
    src = "split the text into sentences"
    assert disambiguate("قسّم النص إلى جمل وبالجمل وللجمل", src) == "قسّم النص إلى جُمَل وبالجُمَل وللجُمَل"
    assert disambiguate("هذه جملة وجملتان", src) == "هذه جملة وجملتان", "جملة is not جمل"


def test_without_a_cue_nothing_changes():
    assert disambiguate("الجمل", "the model chooses the output token") == "الجمل"
    assert disambiguate("", "sentences") == ""


def test_the_ai_writer_is_asked_to_diacritize_ambiguous_words_in_arabic_only():
    from tarjuman.ai.script import script_system_prompt

    assert "tashkeel" in script_system_prompt("ar", "msa")
    assert "tashkeel" not in script_system_prompt("fr", "-")


def test_diacritics_do_not_lengthen_the_speech_estimate():
    from tarjuman.core.text import chars_of

    assert chars_of("الجُمَل الآن") == chars_of("الجمل الآن")
