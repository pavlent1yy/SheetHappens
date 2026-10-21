function sendNotifications() {
  SpreadsheetApp.flush();
  SpreadsheetApp.getActive().getSheetByName('Управление').getRange('B1').setValue(true);
  SpreadsheetApp.getActive().toast('Бот разошлёт уведомления в течение 15 секунд', 'Отправка');
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Бот')
    .addItem('Сохранить и отправить уведомления клиентам', 'sendNotifications')
    .addToUi();
}
