require('dotenv').config(); // Загружаем переменные из .env

const { Telegraf } = require('telegraf');
const cron = require('node-cron');
const fs = require('fs');
const express = require('express');

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHAT_ID = process.env.CHAT_ID;

const bot = new Telegraf(BOT_TOKEN);
const DATA_FILE = 'database.json';

// 📥 Загрузка данных
function loadData() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE));
  } catch {
    return { poll_id: null, answers: {} };
  }
}

// 💾 Сохранение данных
function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

// 📤 Отправка опроса (используется cron и команда /sendpoll)
async function sendPoll() {
  const message = await bot.telegram.sendPoll(
    CHAT_ID,
    'Ты будешь на служении завтра?',
    ['Да', 'Нет'],
    { is_anonymous: false }
  );

  const data = { poll_id: message.poll.id, answers: {} };
  saveData(data);

  await bot.telegram.sendMessage(CHAT_ID, '@all Пожалуйста, ответьте на опрос выше 🙏');
}

// 💬 Обработка ответов на опрос
bot.on('poll_answer', (ctx) => {
  const data = loadData();
  const user = ctx.update.poll_answer.user;
  data.answers[user.id] = {
    name: `${user.first_name} ${user.last_name || ''}`.trim(),
    option_ids: ctx.update.poll_answer.option_ids
  };
  saveData(data);
});

// 📣 Утренний пинг в воскресенье
async function sundayPing() {
  const data = loadData();
  const answers = data.answers || {};
  const answeredYes = [];
  const nonRespondents = [];

  try {
    const members = await bot.telegram.getChatAdministrators(CHAT_ID);
    for (const admin of members) {
      const user = admin.user;
      if (user.is_bot) continue;

      const id = user.id.toString();
      if (!answers[id]) {
        nonRespondents.push(user.username ? `@${user.username}` : user.first_name);
      } else if (answers[id].option_ids.includes(0)) {
        answeredYes.push(user.username ? `@${user.username}` : answers[id].name);
      }
    }

    let text = '⛪ Доброе утро!\n';
    if (answeredYes.length) {
      text += '✅ Кто собирался быть: ' + answeredYes.join(', ') + '\n';
    }
    if (nonRespondents.length) {
      text += '❗ Кто не ответил: ' + nonRespondents.join(', ');
    }

    await bot.telegram.sendMessage(CHAT_ID, text);
  } catch (e) {
    await bot.telegram.sendMessage(CHAT_ID, `Ошибка при сборе пользователей: ${e.message}`);
  }
}

//
// ========== Команды ==========
//

// 👋 /start
bot.start((ctx) =>
  ctx.reply('Привет! 👋 Я бот для опросов перед собранием. В субботу будет опрос, а в воскресенье напоминание.')
);

// 📊 /status — краткий статус
bot.command('status', (ctx) => {
  const data = loadData();
  const total = Object.keys(data.answers).length;
  const yes = Object.values(data.answers).filter(a => a.option_ids.includes(0)).length;

  ctx.reply(`📊 Ответили: ${total}\n✅ Сказали "Да": ${yes}`);
});

// 📋 /answers — подробные ответы
bot.command('answers', (ctx) => {
  const data = loadData();
  const entries = Object.values(data.answers);

  if (!entries.length) {
    return ctx.reply('Пока никто не ответил.');
  }

  let text = '📋 Ответы:\n';
  for (const entry of entries) {
    const choice = entry.option_ids.includes(0) ? '✅ Да' : '❌ Нет';
    text += `• ${entry.name} — ${choice}\n`;
  }

  ctx.reply(text);
});

// 🧹 /clear — сброс базы
bot.command('clear', (ctx) => {
  const cleared = { poll_id: null, answers: {} };
  saveData(cleared);
  ctx.reply('База очищена. Готов к новому опросу.');
});

// 📨 /sendpoll — ручная отправка опроса
bot.command('sendpoll', async (ctx) => {
  try {
    const message = await bot.telegram.sendPoll(
      CHAT_ID,
      'Ты будешь на служении завтра?',
      ['Да', 'Нет'],
      { is_anonymous: false }
    );

    const data = { poll_id: message.poll.id, answers: {} };
    saveData(data);

    await bot.telegram.sendMessage(CHAT_ID, '@all Пожалуйста, ответьте на опрос выше 🙏');
    ctx.reply('✅ Опрос отправлен!');
  } catch (e) {
    ctx.reply(`❌ Ошибка при отправке опроса: ${e.message}`);
  }
});

//
// ========== Планировщик ==========
//

cron.schedule('0 18 * * 6', sendPoll, { timezone: 'Europe/Chisinau' }); // Суббота 18:00
cron.schedule('0 8 * * 0', sundayPing, { timezone: 'Europe/Chisinau' }); // Воскресенье 08:00

//
// ========== HTTP сервер для Render ==========
//

const app = express();
app.get('/', (req, res) => res.send('Бот работает!'));
app.listen(8000, () => console.log('HTTP сервер запущен на порту 8000'));

//
// ========== Запуск бота ==========
//

bot.launch();
console.log('🤖 Бот запущен!');
