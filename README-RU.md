# Magic Lantern RU — dimalishes

Русифицированная Magic Lantern для **Canon EOS 5D Mark II / Canon firmware 2.1.2**.
Версия: `2026-10-28_5D2_ru.212`. База: `ed3e7c0dfacfdeaf3349dee73edf9e3621217462`.
Форк [reticulatedpines/magiclantern_simplified](https://github.com/reticulatedpines/magiclantern_simplified).

## Возможности и исправления

- Русские меню, подсказки и сообщения; переключение русского и английского языка.
- Полная переведённая справка: 206 русских и 204 английские страницы.
- Исправленные переходы к справке из меню и подпунктов.
- Остановка интервалометра кнопкой Play при интервале 0 с.
- Стартовый экран Magic Lantern RU; имя сборщика dimalishes.

## Установка

Готовые комплекты публикуются в [Releases](https://github.com/dimalishes/magiclantern_simplified_ru/releases).
Выпуск содержит два отдельных ZIP: `update` для обновления существующей ML
и `clean_install` для установки с оригинальным установщиком `ML-SETUP.FIR` от 5D2.212.
Обновление самой прошивки Canon до 2.1.2 в комплект не входит.

[Инструкция обновления](doc/ru/INSTALL-UPDATE.md) · [Чистая установка](doc/ru/INSTALL-CLEAN.md)

Delete открывает меню ML, INFO — справку выбранного пункта.
Настройки → Язык меню — выбор языка.

## Проверка

Проверено на личной камере Canon EOS 5D Mark II / Canon 2.1.2
через полное удаление ML и установку с нуля на чистую карту, а так же обновление поверх уже установленного ML.
Другие камеры и весь набор функций/модулей этой русификацией не проверялись.

## Исходники и лицензии

[Сборка](BUILD-RU.md) · [Изменения](RELEASE-NOTES-RU.md).
Словари и инструменты русификации находятся в `localization/`, тексты справки —
в `doc/ru/`, генератор страниц — `tools/ru-help/render.py`.

Русификация: dimalishes. Авторство Magic Lantern и исходные лицензии сохранены:
[COPYING](COPYING), [лицензия DejaVu](localization/DejaVu-LICENSE.txt).
Исходное описание Magic Lantern находится ниже в [README.md](README.md).
