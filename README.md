# Дополнения ConnectTogether

[ConnectTogether](https://connecttogether.ru) — приложение для игры с друзьями по сети без настройки роутера. Дополнение
учит его новой игре: как поставить и запустить её выделенный сервер или, если сервер запускаете вы сами, какие у него
порты и что делать хосту. Дополнение — это один файл `addon.json`, код писать не нужно.

Что здесь лежит:

- [`addons/`](addons) — дополнения сообщества, по папке на игру;
- [`docs/format.md`](docs/format.md) — формат `addon.json`: все поля, правила и примеры;
- [`schema/addon.schema.json`](schema/addon.schema.json) — JSON-схема: с ней редактор подсказывает поля и подчёркивает ошибки;
- [`examples/`](examples) — дополнения, встроенные в приложение, и пример Factorio — сервер с инструкцией.

## Как установить дополнение

1. Откройте папку игры в [`addons/`](addons) и скачайте её `addon.json` (кнопка «Download raw file»).
2. В ConnectTogether откройте **Настройки → Игры → «Добавить из файла»** и выберите скачанный файл. Можно и проще:
   переименуйте его в `<id>.ctaddon` и откройте двойным щелчком — приложение покажет то же окно.
3. Приложение покажет, что дополнение будет делать: что скачает и откуда, что запустит, какие порты откроет друзьям.
   Если всё так, нажмите «Добавить» — игра сразу появится в «Создать комнату».

Дополнения отсюда проходят автоматическую проверку и просмотр командой ConnectTogether. Но ставите вы их сами:
смотрите, что показывает окно «Добавить из файла».

## Как сделать своё дополнение

1. Скопируйте пример, который ближе к вашей игре:
   - [`examples/minecraft`](examples/minecraft/addon.json) — сервер скачивается по https с проверкой хэша, лицензия, настройки;
   - [`examples/rust`](examples/rust/addon.json) — выделенный сервер из Steam через SteamCMD, консоль по RCON;
   - [`examples/terraria`](examples/terraria/addon.json) — сервер по https с хэшем, настройки мира, консоль `terminal`
     для сервера, который читает команды по клавишам;
   - [`examples/valheim`](examples/valheim/addon.json) — SteamCMD, сервер без команд: лог из файла, остановка по Ctrl+C;
   - [`examples/project-zomboid`](examples/project-zomboid/addon.json) — SteamCMD, Java-сервер запускается напрямую,
     порты и слоты в его ini, команды в стандартный ввод;
   - [`examples/palworld`](examples/palworld/addon.json) — SteamCMD, настройки в INI Unreal Engine (`OptionSettings`),
     консоль по RCON, перед остановкой — сохранение;
   - [`examples/enshrouded`](examples/enshrouded/addon.json) — SteamCMD, настройки в JSON, группа игроков задаётся из
     манифеста;
   - [`examples/core-keeper`](examples/core-keeper/addon.json) — SteamCMD, остановка «закрыть окно», строка для входа
     `{ip};{port};;пароль`;
   - [`examples/7-days-to-die`](examples/7-days-to-die/addon.json) — SteamCMD, настройки аргументами, консоль по telnet;
   - [`examples/factorio`](examples/factorio/addon.json) — сервер с инструкцией: хост запускает игру сам, приложение
     подсказывает шаги и открывает порты друзьям; так же устроен [Minecraft Bedrock](examples/minecraft-bedrock/addon.json).
2. Откройте `addon.json` в VS Code: строка `"$schema"` включает подсказки по полям. Все поля описаны в
   [`docs/format.md`](docs/format.md). Или откройте в ConnectTogether **Настройки → Игры → «Сделать дополнение»**:
   там шаблоны встроенных игр, проверка на лету и сохранение в `.ctaddon`.
3. Проверьте файл программой `addon-check` — её можно скачать из
   [релизов](https://github.com/kreker0001/ConnectTogether-Addons/releases):

   ```
   addon-check-win-x64.exe addon.json
   ```

   Те же ошибки покажет и приложение в «Добавить из файла».
4. Добавьте дополнение в ConnectTogether и попробуйте всё целиком: установка, запуск, комната, друг заходит по адресу.
   Исправили файл — добавьте его снова: новая версия заменит прежнюю.
5. Пришлите дополнение сюда — как это сделать, написано в [CONTRIBUTING.md](CONTRIBUTING.md).

## Дополнения

| Игра | Папка | Вид | Автор |
|---|---|---|---|

Пока пусто — пришлите первое.

Эти игры уже встроены в приложение, ставить их отсюда не нужно: Minecraft (Java и Bedrock), Rust, Terraria, Valheim,
7 Days to Die, Project Zomboid, Palworld, V Rising, Enshrouded, Satisfactory и Core Keeper. Их манифесты лежат в [`examples/`](examples) — с них удобно начинать своё.

## Лицензия

[MIT](LICENSE): манифесты, схему, документацию и addon-check можно копировать и менять, сохранив строку об авторстве.
Присылая дополнение, вы соглашаетесь выложить его на тех же условиях.
