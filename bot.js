require('dotenv').config();

const { Telegraf } = require('telegraf');
const cron = require('node-cron');
const fs = require('fs');
const express = require('express');

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHAT_ID = process.env.CHAT_ID;
const WEBHOOK_PATH = '/webhook'; // безопасный путь
const PORT = process.env.PORT || 8000;

const bot = new Telegraf(BOT_TOKEN);
const DATA_FILE = 'database.json';

// 📥 Загрузка данных
function loadData() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE));
  } catch {
    return { poll_id: null, answers: {}, poll_sent_at: null };
  }
}

// 💾 Сохранение данных
function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

// 📤 Отправка опроса
async function sendPoll(manual = false) {
  const data = loadData();

  if (!manual) {
    const today = new Date().toISOString().slice(0, 10);
    if (data.poll_sent_at === today) return; // уже отправлен
  }

  const message = await bot.telegram.sendPoll(
    CHAT_ID,
    'Ты будешь на служении завтра?',
    ['Да', 'Нет'],
    { is_anonymous: false }
  );

  const now = new Date().toISOString().slice(0, 10);
  const updatedData = {
    poll_id: message.poll.id,
    answers: {},
    poll_sent_at: now,
  };

  saveData(updatedData);
  await bot.telegram.sendMessage(CHAT_ID, '@all Пожалуйста, ответьте на опрос выше 🙏');
}

// 💬 Ответы на опрос
bot.on('poll_answer', (ctx) => {
  const data = loadData();
  const user = ctx.update.poll_answer.user;

  data.answers[user.id] = {
    name: `${user.first_name} ${user.last_name || ''}`.trim(),
    option_ids: ctx.update.poll_answer.option_ids
  };

  saveData(data);
});

// 📣 Утреннее воскресное напоминание
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

bot.start((ctx) => ctx.reply('Привет! 👋 Я бот для опросов перед собранием. В субботу будет опрос, а в воскресенье напоминание.'));

bot.command('status', (ctx) => {
  const data = loadData();
  const total = Object.keys(data.answers).length;
  const yes = Object.values(data.answers).filter(a => a.option_ids.includes(0)).length;

  ctx.reply(`📊 Ответили: ${total}\n✅ Сказали "Да": ${yes}`);
});

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

bot.command('clear', (ctx) => {
  const cleared = { poll_id: null, answers: {}, poll_sent_at: null };
  saveData(cleared);
  ctx.reply('База очищена. Готов к новому опросу.');
});

bot.command('sendpoll', async (ctx) => {
  try {
    await sendPoll(true); // ручной запуск
    ctx.reply('✅ Опрос отправлен!');
  } catch (e) {
    ctx.reply(`❌ Ошибка при отправке опроса: ${e.message}`);
  }
});

//
// ========== Планировщик ==========
//

cron.schedule('0 18 * * 6', () => sendPoll(false), { timezone: 'Europe/Chisinau' }); // Суббота 18:00
cron.schedule('59 23 * * 6', () => sendPoll(false), { timezone: 'Europe/Chisinau' }); // Подстраховка в 23:59
cron.schedule('0 8 * * 0', sundayPing, { timezone: 'Europe/Chisinau' }); // Воскресенье 08:00

//
// ========== Webhook для Render ==========
//

const app = express();
app.use(express.json());
app.use(bot.webhookCallback(WEBHOOK_PATH));
app.get('/', (req, res) => res.send('Бот работает через Webhook ✅'));

app.listen(PORT, async () => {
  const webhookUrl = `https://${process.env.RENDER_EXTERNAL_URL || 'telegrambotreminder-pn1p.onrender.com'}${WEBHOOK_PATH}`;
  await bot.telegram.setWebhook(webhookUrl);
  console.log(`🤖 Бот запущен через Webhook на ${webhookUrl}`);
});
