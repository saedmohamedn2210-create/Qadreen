import ctypes
import ctypes.wintypes
import base64
import logging

log = logging.getLogger("qadreen.crypto_manager")

class DATA_BLOB(ctypes.Structure):
	_fields_ = [("cbData", ctypes.wintypes.DWORD),
				("pbData", ctypes.POINTER(ctypes.c_char))]

def encrypt_token(plain_text):
	"""
	Encrypts a token using Windows DPAPI and returns a base64 string prefixed with dpapi:v1:.
	If the token is empty, returns it as is.
	"""
	if not plain_text:
		return plain_text

	try:
		plain_bytes = plain_text.encode('utf-8')
		data_in = DATA_BLOB(len(plain_bytes), ctypes.cast(ctypes.c_char_p(plain_bytes), ctypes.POINTER(ctypes.c_char)))
		data_out = DATA_BLOB()
		
		# CryptProtectData(pDataIn, szDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
		# dwFlags: CRYPTPROTECT_UI_FORBIDDEN = 0x1
		if ctypes.windll.crypt32.CryptProtectData(ctypes.byref(data_in), None, None, None, None, 0x01, ctypes.byref(data_out)):
			encrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
			ctypes.windll.kernel32.LocalFree(data_out.pbData)
			b64_str = base64.b64encode(encrypted_bytes).decode('utf-8')
			return "dpapi:v1:" + b64_str
		else:
			log.error("DPAPI CryptProtectData failed.")
			return ""
	except Exception as e:
		log.error("Error during encryption: %s", e)
		return ""

def decrypt_token(cipher_text):
	"""
	Decrypts a dpapi:v1: prefixed token.
	If the prefix is missing, treats it as legacy plaintext and returns it as is.
	If decryption fails, returns an empty string.
	"""
	if not cipher_text:
		return ""
	
	if not cipher_text.startswith("dpapi:v1:"):
		return cipher_text
	
	try:
		b64_str = cipher_text[len("dpapi:v1:"):]
		encrypted_bytes = base64.b64decode(b64_str)
		data_in = DATA_BLOB(len(encrypted_bytes), ctypes.cast(ctypes.c_char_p(encrypted_bytes), ctypes.POINTER(ctypes.c_char)))
		data_out = DATA_BLOB()
		
		# CryptUnprotectData(pDataIn, ppszDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
		if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(data_in), None, None, None, None, 0x01, ctypes.byref(data_out)):
			decrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
			ctypes.windll.kernel32.LocalFree(data_out.pbData)
			return decrypted_bytes.decode('utf-8')
		else:
			log.error("DPAPI CryptUnprotectData failed.")
			return ""
	except Exception as e:
		log.error("Error during decryption: %s", e)
		return ""
