import os
import mysql.connector
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ParseMode, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Cargar las variables de entorno
load_dotenv()

# Configurar los detalles de conexión a la base de datos MySQL
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

# Realizar la solicitud HTTP y analizar el contenido HTML
url = requests.get("https://www.bcv.org.ve/")
soup = BeautifulSoup(url.content, "html.parser")

# Encontrar todas las etiquetas div con la clase "col-sm-6 col-xs-6 centrado"
divs = soup.find_all("div", class_="col-sm-6 col-xs-6 centrado")

# Verificar si hay al menos cinco etiquetas div con esa clase
if len(divs) >= 5:
    # Obtener la quinta etiqueta div
    resultado_div = divs[4]

    # Obtener el texto del elemento y eliminar las comas
    resultado_texto = resultado_div.get_text().strip().replace(',', '')

    # Convertir el texto a número flotante
    resultado_numero = float(resultado_texto) / 100000000

    # Aproximar el número a dos dígitos después del punto decimal
    resultado_aproximado = round(resultado_numero, 2)

    # Formatear el número como "XX,XX"
    resultado_final = "{:.2f}".format(resultado_aproximado).replace('.', ',')

# Configurar el token del bot de Telegram
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

# Configuración de botones (deja esta parte sin cambios)
def start(update, context):
    keyboard_options = [
        ["🌐 Página web", "💰 Tasa BCV"],
        ["🏧 Consultar saldo", "🏦 Cuentas bancarias", "🔗 Link del portal"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard_options, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Elige una opción del menú:", reply_markup=reply_markup)

def handle_option_1(update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = "Aquí tienes el enlace a la página web:\n[ICAROSoft](https://icarosoft.com)"
    context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode=ParseMode.MARKDOWN_V2)

def handle_option_2(update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = "La tasa BCV es: {}".format(resultado_final)
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)

def handle_option_3(update, context):
    # Solicitar al usuario que ingrese su cédula
    context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, ingrese su número de documento con el siguiente formato:\n\nVXXXXXXXX o JXXXXXXXXX")
    # Establecer un estado para esperar la cédula del usuario
    context.user_data['waiting_for_cedula'] = True

# Nueva función para la opción 4 (Cuentas bancarias)
def handle_option_4(update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = "Nuestra cuentas bancarias son:\n\nBanco de Venezuela 🔴\n--------------------------------\nCuenta Corriente: 0102-XXXX-XX-XXXXXXXXXX\nNombre: Ronald Perera\nCédula: V18122849\n\nPago móvil 📱\n------------------\nCédula: 18122849\nBanco: Banco de Venezuela\nTeléfono: 0412-5927917"
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Nueva función para la opción 5 (Link del portal)
def handle_option_5(update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = "Por favor, ingrese su número de documento con el siguiente formato:\n\nVXXXXXXXX o JXXXXXXXXX"
    context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode=ParseMode.MARKDOWN_V2)
    # Establecer un estado para esperar la cédula del usuario
    context.user_data['waiting_for_cedula_portal'] = True

def buscar_id_cliente_y_clave_portal(update, context):
    cedula = context.user_data.get('cedula_portal')

    # Conectar a la base de datos MySQL
    cnx = mysql.connector.connect(host=db_host, user=db_user, password=db_password, database=db_name, ssl_disabled=True)

    if cnx.is_connected():
        cursor = cnx.cursor()
        try:
            # Ejecutar la consulta SQL con la cédula del usuario y las condiciones adicionales
            query = "SELECT id_cliente, clave FROM clientes_datos WHERE empresa='tecnoven' AND sucursal='maracaibo' AND cod_cliente = %s"
            cursor.execute(query, (cedula,))

            # Obtener los resultados
            results = cursor.fetchall()

            if results:
                id_cliente, clave = results[0]
                context.user_data['id_cliente_portal'] = id_cliente
                context.user_data['clave_portal'] = clave
                # Generar el enlace con los datos y enviarlo al usuario
                generar_enlace_portal_y_enviar(update, context)
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="No se encontraron datos para el documento proporcionado.")
        except mysql.connector.Error as error:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Ocurrió un error al ejecutar la consulta: {error}")
        finally:
            cursor.close()
            cnx.close()
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No se pudo establecer la conexión a la base de datos.")

def generar_enlace_portal_y_enviar(update, context):
    id_cliente = context.user_data.get('id_cliente_portal')
    clave = context.user_data.get('clave_portal')

    if id_cliente and clave:
        enlace = f"https://cliente.icarosoft.com/Login/?user={id_cliente}&pass={clave}"
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Aquí tienes el enlace al portal:\n{enlace}")
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No se encontraron datos para generar el enlace.")

def chat(update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    # Obtener el mensaje del usuario
    user_message = update.message.text

    # Verificar si estamos esperando la cédula del usuario
    if context.user_data.get('waiting_for_cedula'):
        # Si estamos esperando la cédula, utilizar el mensaje como consulta en la base de datos
        cedula = user_message

        # Conectar a la base de datos MySQL
        cnx = mysql.connector.connect(host=db_host, user=db_user, password=db_password, database=db_name, ssl_disabled=True)

        # Validar la conexión y ejecutar la consulta
        if cnx.is_connected():
            cursor = cnx.cursor()
            try:
                # Ejecutar la consulta SQL con la cédula del usuario y las condiciones adicionales
                query = "SELECT saldo FROM clientes_datos WHERE empresa='tecnoven' AND sucursal='maracaibo' AND cod_cliente = %s"
                cursor.execute(query, (cedula,))

                # Obtener los resultados
                results = cursor.fetchall()

                if results:
                    saldo = results[0][0]
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"La deuda de su factura es: $ {saldo}")
                else:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="No se encontró una factura con deuda para ese documento")
            except mysql.connector.Error as error:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Ocurrió un error al ejecutar la consulta: {error}")
            finally:
                cursor.close()
                cnx.close()
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="No se pudo establecer la conexión a la base de datos.")

        # Reiniciar el estado de espera de la cédula
        del context.user_data['waiting_for_cedula']
    elif context.user_data.get('waiting_for_cedula_portal'):
        cedula = user_message
        context.user_data['cedula_portal'] = cedula
        buscar_id_cliente_y_clave_portal(update, context)
        del context.user_data['waiting_for_cedula_portal']
    else:
        # Respuesta si no se espera la cédula
        response = "Lo siento, no tengo una respuesta para eso."
        context.bot.send_message(chat_id=update.effective_chat.id, text=response)

def main():
    # Crear una instancia de Updater y pasarle el token del bot de Telegram
    updater = Updater(token=telegram_token, use_context=True)

    # Obtener el despachador para registrar los manejadores
    dispatcher = updater.dispatcher

    # Registrar el manejador para la opción 1 del teclado
    option_1_handler = MessageHandler(Filters.regex('^🌐 Página web$'), handle_option_1)
    dispatcher.add_handler(option_1_handler)

    # Registrar el manejador para la opción 2 del teclado
    option_2_handler = MessageHandler(Filters.regex('^💰 Tasa BCV$'), handle_option_2)
    dispatcher.add_handler(option_2_handler)

    # Registrar el manejador para la opción 3 del teclado
    option_3_handler = MessageHandler(Filters.regex('^🏧 Consultar saldo$'), handle_option_3)
    dispatcher.add_handler(option_3_handler)

    # Registrar el manejador para la opción 4 del teclado
    option_4_handler = MessageHandler(Filters.regex('^🏦 Cuentas bancarias$'), handle_option_4)
    dispatcher.add_handler(option_4_handler)

    # Registrar el manejador para la opción 5 del teclado (Ir al Portal)
    option_5_handler = MessageHandler(Filters.regex('^🔗 Link del portal$'), handle_option_5)
    dispatcher.add_handler(option_5_handler)


    # Registrar el manejador para el comando "/start"
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # Registrar el manejador para los mensajes de texto
    chat_handler = MessageHandler(Filters.text & (~Filters.command), chat)
    dispatcher.add_handler(chat_handler)

    # Iniciar el bot
    updater.start_polling()
    # Mantener el bot en ejecución hasta que se presione Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
