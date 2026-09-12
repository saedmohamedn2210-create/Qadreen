# -*- coding: utf-8 -*-
# globalPlugin.py
# إضافة Qadreen - إدارة ومشاركة روابط البرامج
# يغطي هذا الملف: وضع العرض (Search and Fetch)، وضع التصميم (Design Mode)،
# وصفحة إعدادات لغة الإضافة داخل NVDA Settings.

import os
import base64
import copy
import json
import time
import tempfile
import threading
import webbrowser
import urllib.parse
import urllib.error
import urllib.request
import globalVars

import wx
import api
import ui
import gui
import config
import languageHandler
import addonHandler
import globalPluginHandler
from scriptHandler import script
from logHandler import log

try:
	from . import crypto_manager
except (ImportError, ValueError):
	try:
		import crypto_manager
	except ImportError:
		log.error("Qadreen: Failed to import crypto_manager. Tokens will not be encrypted.", exc_info=True)
		class _FallbackCryptoManager:
			@staticmethod
			def encrypt_token(plain_text):
				return plain_text
			@staticmethod
			def decrypt_token(cipher_text):
				if cipher_text and cipher_text.startswith("dpapi:v1:"):
					return ""
				return cipher_text
		crypto_manager = _FallbackCryptoManager()


# مسار ملف بيانات Qadreen الدائم داخل إعدادات NVDA
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(globalVars.appArgs.configPath, "qadreen_data.json")


# =====================================================================
# نظام الترجمة الداخلي للإضافة (مستقل عن نظام gettext القياسي في NVDA)
# لأن المستخدم يحتاج التحكم بلغة الإضافة بشكل منفصل عن لغة NVDA نفسها
# =====================================================================

STRINGS = {
	"scriptDescription": {
		"ar": "فتح نافذة البحث السريع عن روابط البرامج",
		"en": "Open the quick link search window"
	},
	"helpScriptDescription": {
		"ar": "فتح نافذة مساعدة الإضافة",
		"en": "Open the add-on help window"
	},
	"quickAddScriptDescription": {
		"ar": "إضافة رابط سريع من الحافظة إلى إضافة قادرين",
		"en": "Quickly add a link from the clipboard to Qadreen"
	},
	"dialogTitleView": {"ar": "قادرين - بحث سريع عن الروابط", "en": "Qadreen - Quick Link Search"},
	"dialogTitleDesign": {"ar": "قادرين - وضع التصميم", "en": "Qadreen - Design Mode"},
	"searchLabel": {"ar": "بحث:", "en": "Search:"},
	"searchCtrlName": {"ar": "مربع البحث السريع", "en": "Quick search box"},
	"groupLabel": {"ar": "المجموعة (Group)", "en": "Group"},
	"groupListName": {"ar": "قائمة المجموعات", "en": "Groups list"},
	"categoryLabel": {"ar": "الفئة (Category)", "en": "Category"},
	"categoryListName": {"ar": "قائمة الفئات", "en": "Categories list"},
	"softwareLabel": {"ar": "البرنامج (Software)", "en": "Software"},
	"softwareListName": {"ar": "قائمة البرامج", "en": "Software list"},
	"copyButton": {"ar": "نسخ الرابط", "en": "Copy link"},
	"addToCopyButton": {"ar": "إضافة إلى النسخ", "en": "Add to copy"},
	"closeButton": {"ar": "إغلاق", "en": "Close"},
	"msgNoSoftwareSelected": {"ar": "لم يتم تحديد برنامج", "en": "No software selected"},
	"msgNoLink": {"ar": "لا يوجد رابط لهذا البرنامج", "en": "This software has no link"},
	"msgCopied": {"ar": "تم النسخ", "en": "Copied"},
	"msgOpeningLink": {"ar": "جاري فتح الرابط", "en": "Opening the link"},
	"msgDesignMode": {"ar": "وضع التصميم", "en": "Design mode"},
	"msgViewMode": {"ar": "وضع العرض", "en": "View mode"},
	"msgSelectGroupFirst": {"ar": "الرجاء اختيار مجموعة أولاً", "en": "Please select a group first"},
	"msgSelectGroupAndCategoryFirst": {"ar": "الرجاء اختيار مجموعة وفئة أولاً", "en": "Please select a group and category first"},
	"msgNameRequired": {"ar": "يجب إدخال اسم", "en": "A name is required"},
	"msgSoftwareNameRequired": {"ar": "يجب إدخال اسم البرنامج", "en": "Software name is required"},
	"msgUrlRequired": {"ar": "يجب إدخال الرابط", "en": "The link is required"},
	"msgUrlExists": {"ar": "هذا الرابط موجود مسبقاً في قاعدة البيانات", "en": "This link already exists in the database"},
	"msgNameExists": {"ar": "هذا الاسم موجود مسبقاً", "en": "This name already exists"},
	"msgNameExistsInGroup": {"ar": "هذا الاسم موجود مسبقاً في هذه المجموعة", "en": "This name already exists in this group"},
	"msgNameExistsInCategory": {"ar": "هذا الاسم موجود مسبقاً في هذه الفئة", "en": "This name already exists in this category"},
	"msgAdded": {"ar": "تمت الإضافة", "en": "Added"},
	"msgEdited": {"ar": "تم التعديل", "en": "Edited"},
	"msgDeleted": {"ar": "تم الحذف", "en": "Deleted"},
	"msgSelectItemFirst": {"ar": "حدد عنصراً أولاً", "en": "Select an item first"},
	"msgNoGroupSelected": {"ar": "لم يتم تحديد مجموعة", "en": "No group selected"},
	"msgNoCategorySelected": {"ar": "لم يتم تحديد فئة", "en": "No category selected"},
	"addGroupTitle": {"ar": "إضافة مجموعة", "en": "Add group"},
	"editGroupTitle": {"ar": "تعديل اسم المجموعة", "en": "Edit group name"},
	"groupNameLabel": {"ar": "اسم المجموعة", "en": "Group name"},
	"addCategoryTitle": {"ar": "إضافة فئة", "en": "Add category"},
	"editCategoryTitle": {"ar": "تعديل اسم الفئة", "en": "Edit category name"},
	"categoryNameLabel": {"ar": "اسم الفئة", "en": "Category name"},
	"addSoftwareTitle": {"ar": "إضافة برنامج", "en": "Add software"},
	"editSoftwareTitle": {"ar": "تعديل بيانات البرنامج", "en": "Edit software details"},
	"softwareNameLabel": {"ar": "اسم البرنامج", "en": "Software name"},
	"urlLabel": {"ar": "الرابط الأساسي", "en": "Main link"},
	"url2Label": {"ar": "رابط إضافي (اختياري)", "en": "Additional link (optional)"},
	"notesLabel": {"ar": "الملاحظات", "en": "Notes"},
	"confirmDeleteTitle": {"ar": "تأكيد الحذف", "en": "Confirm delete"},
	"confirmDeleteGroup": {"ar": 'سيتم حذف المجموعة "{}" وكل ما بداخلها من فئات وبرامج. متابعة؟', "en": 'Group "{}" and everything inside it (categories and software) will be deleted. Continue?'},
	"confirmDeleteCategory": {"ar": 'سيتم حذف الفئة "{}" وكل ما بداخلها من برامج. متابعة؟', "en": 'Category "{}" and everything inside it (software) will be deleted. Continue?'},
	"confirmDeleteSoftware": {"ar": 'سيتم حذف البرنامج "{}". متابعة؟', "en": 'Software "{}" will be deleted. Continue?'},
	"settingsCategoryTitle": {"ar": "قادرين", "en": "Qadreen"},
	"settingsLanguageLabel": {"ar": "لغة الإضافة", "en": "Add-on language"},
	"settingsFollowNVDA": {"ar": "اتباع لغة NVDA", "en": "Follow NVDA language"},
	"settingsAlwaysArabic": {"ar": "العربية دائماً", "en": "Always Arabic"},
	"settingsAlwaysEnglish": {"ar": "الإنجليزية دائماً", "en": "Always English"},
	"importButton": {"ar": "استيراد بيانات", "en": "Import data"},
	"importDialogTitle": {"ar": "اختر ملف البيانات المراد استيراده", "en": "Choose the data file to import"},
	"msgImportFailed": {"ar": "تعذر قراءة الملف المحدد", "en": "Could not read the selected file"},
	"msgImportSummary": {"ar": "تم الاستيراد: {} عنصر جديد، {} نسخة إضافية بنفس الاسم برابط مختلف", "en": "Import complete: {} new items, {} additional copies with a different link"},
	"msgNoOtherGroup": {"ar": "لا توجد مجموعة أخرى لنقل إليها", "en": "There is no other group to move to"},
	"msgNoCategoryInGroup": {"ar": "هذه المجموعة لا تحتوي فئات بعد", "en": "This group has no categories yet"},
	"msgSameLocation": {"ar": "البرنامج موجود بالفعل في هذا المكان", "en": "The software is already in this location"},
	"msgMoved": {"ar": "تم النقل", "en": "Moved"},
	"moveGroupTitle": {"ar": "نقل/دمج المجموعة إلى", "en": "Move/merge group to"},
	"moveCategoryTitle": {"ar": "نقل الفئة إلى مجموعة", "en": "Move category to group"},
	"moveSoftwareGroupTitle": {"ar": "نقل البرنامج - اختر المجموعة", "en": "Move software - choose group"},
	"moveSoftwareCategoryTitle": {"ar": "نقل البرنامج - اختر الفئة", "en": "Move software - choose category"},
	"confirmMoveTitle": {"ar": "تأكيد النقل", "en": "Confirm move"},
	"confirmMoveGroup": {
		"ar": 'سيتم دمج المجموعة "{}" بالكامل داخل المجموعة "{}". العناصر المشتركة ستُستبدل ببيانات المصدر، والمجموعة الأصلية ستُحذف بعد الدمج. متابعة؟',
		"en": 'Group "{}" will be fully merged into group "{}". Shared items will be overwritten by the source data, and the original group will be deleted after merging. Continue?'
	},
	"confirmMoveCategory": {
		"ar": 'سيتم نقل الفئة "{}" من المجموعة "{}" إلى المجموعة "{}". إن وُجدت فئة بنفس الاسم هناك سيتم الدمج معها. متابعة؟',
		"en": 'Category "{}" will be moved from group "{}" to group "{}". If a category with the same name exists there, it will be merged. Continue?'
	},
	"confirmMoveSoftware": {
		"ar": 'سيتم نقل البرنامج "{}" إلى: {} / {}. إن وُجد برنامج بنفس الاسم سيتم ترقيمه تلقائياً. متابعة؟',
		"en": 'Software "{}" will be moved to: {} / {}. If a software with the same name exists there, it will be numbered automatically. Continue?'
	},
	"contactDeveloperButton": {"ar": "تواصل مع المطور عبر البريد الإلكتروني", "en": "Contact the developer by email"},
	"helpDialogTitle": {"ar": "مساعدة إضافة قادرين", "en": "Qadreen add-on help"},
	"helpCloseButton": {"ar": "إغلاق", "en": "Close"},
	"msgUpdateAvailable": {
		"ar": "يتوفر تحديث جديد لإضافة قادرين: الإصدار {}. يمكنك تنزيله من صفحة المشروع على GitHub.",
		"en": "A new Qadreen update is available: version {}. You can download it from the project's GitHub page."
	},
	"updateAvailableTitle": {"ar": "تحديث جديد متاح", "en": "New update available"},
	"msgUpdateConfirm": {
		"ar": "يتوفر إصدار جديد من إضافة قادرين: {}. هل تريد تنزيله وتثبيته الآن؟ بياناتك ستبقى محفوظة.",
		"en": "A new Qadreen version is available: {}. Download and install it now? Your data will be kept."
	},
	"updateInstalledTitle": {"ar": "اكتمل التحديث", "en": "Update complete"},
	"msgUpdateInstalledRestart": {
		"ar": "تم تثبيت التحديث بنجاح، وبياناتك محفوظة كما هي. يجب إعادة تشغيل NVDA لتفعيل النسخة الجديدة. إعادة التشغيل الآن؟",
		"en": "The update was installed successfully, and your data has been kept. NVDA must restart to activate the new version. Restart now?"
	},
	"msgUpdateAssetNotFound": {"ar": "تعذر إيجاد ملف التثبيت في هذا الإصدار", "en": "Could not find the installer file in this release"},
	"msgUpdateDownloadFailed": {"ar": "تعذر تنزيل التحديث", "en": "Failed to download the update"},
	"msgUpdateInstallFailed": {"ar": "تعذر تثبيت التحديث", "en": "Failed to install the update"},
	"createNewChoice": {"ar": "إنشاء جديد...", "en": "Create new..."},
	"quickAddGroupTitle": {"ar": "اختر المجموعة", "en": "Choose group"},
	"quickAddCategoryTitle": {"ar": "اختر الفئة", "en": "Choose category"},
	"msgClipboardEmpty": {"ar": "لا يوجد نص في الحافظة، انسخ الرابط أولاً", "en": "The clipboard has no text, copy the link first"},
	"settingsModeLabel": {"ar": "نمط عمل الإضافة", "en": "Add-on operation mode"},
	"settingsOfflineMode": {"ar": "محلي (بدون إنترنت)", "en": "Offline (local only)"},
	"settingsOnlineMode": {"ar": "تعاوني (مزامنة سحابية)", "en": "Online (cloud sync)"},
	"settingsGistIdLabel": {"ar": "معرف Gist", "en": "Gist ID"},
	"settingsPatLabel": {"ar": "مفتاح الوصول الشخصي (PAT)", "en": "Personal Access Token (PAT)"},
	"settingsPatWarning": {
		"ar": "تنبيه: يُخزَّن هذا المفتاح كنص عادي غير مشفّر في إعدادات NVDA. استخدم مفتاحاً بصلاحية gist فقط، ولا تستخدم مفتاحاً له أي صلاحيات إضافية على حسابك.",
		"en": "Warning: this token is stored as plain, unencrypted text in NVDA's settings. Use a token scoped to gist access only, never one with broader account permissions."
	},
	"settingsSourceTypeLabel": {"ar": "مصدر المزامنة", "en": "Sync source"},
	"settingsSourceGist": {"ar": "Gist", "en": "Gist"},
	"settingsSourceRepo": {"ar": "مستودع (Repository)", "en": "Repository"},
	"settingsRepoOwnerNameLabel": {"ar": "المستودع (المالك/الاسم)", "en": "Repository (owner/name)"},
	"settingsRepoPathLabel": {"ar": "مسار الملف داخل المستودع", "en": "File path inside the repository"},
	"settingsRepoBranchLabel": {"ar": "الفرع (Branch)", "en": "Branch"},
	"settingsRepoPatLabel": {"ar": "مفتاح الوصول الشخصي (PAT) للمستودع", "en": "Personal Access Token (PAT) for the repository"},
	"settingsRepoPatWarning": {
		"ar": "لهذا المفتاح صلاحيات أوسع من مفتاح Gist. للمستودعات العامة استخدم صلاحية public_repo فقط. للمستودعات الخاصة، يُفضَّل توكن Fine-grained محدد بمستودع واحد وصلاحية Contents: Read and write فقط، بدلاً من صلاحية repo الكلاسيكية الكاملة.",
		"en": "This token needs broader permissions than the Gist token. For public repositories, use the public_repo scope only. For private repositories, prefer a fine-grained token limited to this one repository with Contents: Read and write access, instead of the full classic repo scope."
	},
	"msgOnlineModeRequired": {"ar": "هذا الاختصار يعمل فقط في الوضع التعاوني (Online)", "en": "This shortcut only works in Online mode"},
	"msgSelectGroupOrCategoryFirst": {"ar": "قف على مجموعة أو فئة أولاً", "en": "Stand on a group or category first"},
	"msgSharingEnabled": {"ar": "تم تفعيل المشاركة", "en": "Sharing enabled"},
	"msgSharingDisabled": {"ar": "تم إيقاف المشاركة", "en": "Sharing disabled"},
	"onlineDesignModeScriptDescription": {
		"ar": "تبديل وضع التصميم السحابي (للمالك فقط)",
		"en": "Toggle Online Design Mode (Owner only)"
	},
	"msgOnlineDesignOffline": {
		"ar": "وضع التصميم السحابي غير متاح في الوضع المحلي (Offline)",
		"en": "Online Design Mode is not available in Offline mode"
	},
	"msgGitHubCredentialsMissing": {
		"ar": "بيانات GitHub ناقصة، تأكد من اسم مالك المستودع ورمز PAT في الإعدادات",
		"en": "GitHub credentials missing, check repo owner and PAT in settings"
	},
	"msgVerifyingUser": {
		"ar": "جاري التحقق من هوية مستخدم GitHub...",
		"en": "Verifying GitHub user identity..."
	},
	"msgAuthInProgress": {
		"ar": "عملية التحقق جارية بالفعل، يرجى الانتظار",
		"en": "Authentication is already in progress, please wait"
	},
	"msgOwnerOnly": {
		"ar": "وضع التصميم السحابي مخصص لمالك المستودع فقط",
		"en": "Online Design Mode is restricted to the repository owner only"
	},
	"msgOnlineDesignModeEnabled": {
		"ar": "تم التحقق من ملكية المستودع. تم تفعيل وضع التصميم السحابي بنجاح.",
		"en": "Online Design Mode enabled"
	},
	"msgOnlineDesignModeDisabled": {
		"ar": "تم إيقاف وضع التصميم السحابي",
		"en": "Online Design Mode disabled"
	},
	"msgAuthFailed": {
		"ar": "تعذر التحقق من هوية GitHub، تأكد من اتصال الإنترنت وصلاحية PAT",
		"en": "Could not verify GitHub identity, check connection and PAT validity"
	},
	"deletedItemsScriptDescription": {
		"ar": "فتح قائمة العناصر المحذوفة (Blacklist)",
		"en": "Open deleted items list (Blacklist)"
	},
	"deletedItemsDialogTitle": {
		"ar": "قادرين - العناصر المحذوفة",
		"en": "Qadreen - Deleted Items"
	},
	"deletedItemsListLabel": {
		"ar": "قائمة البرامج المحذوفة:",
		"en": "Deleted software list:"
	},
	"removeBlacklistButton": {
		"ar": "إزالة من القائمة (Delete)",
		"en": "Remove from blacklist (Delete)"
	},
	"labelLocal": {
		"ar": "محلي",
		"en": "Local"
	},
	"labelCloud": {
		"ar": "سحابي",
		"en": "Cloud"
	},
	"msgNoDeletedItems": {
		"ar": "لا توجد عناصر محذوفة",
		"en": "No deleted items"
	},
	"msgItemRemovedFromBlacklist": {
		"ar": "تمت إزالة العنصر من قائمة المحذوفات",
		"en": "Item removed from blacklist"
	},
}


def getLanguage():
	"""تحديد لغة واجهة الإضافة الحالية مع تأمين ضد أخطاء التهيئة المبكرة"""
	try:
		setting = config.conf["qadreen"]["language"]
	except KeyError:
		setting = "follow"

	if setting == "ar":
		return "ar"

	if setting == "en":
		return "en"

	# follow: اتباع لغة NVDA الحالية
	nvdaLang = languageHandler.getLanguage()
	return "ar" if nvdaLang.startswith("ar") else "en"


HELP_TEXT = {
	"ar": """مساعدة إضافة قادرين

الاختصار العام
Insert+Control+Q: فتح نافذة الإضافة، تفتح دائماً على وضع العرض.
Insert+Control+H: فتح نافذة المساعدة هذه.
Insert+Shift+C: إضافة سريعة من أي برنامج آخر (متصفح، تليجرام، واتساب). انسخ الرابط أولاً بطريقتك المعتادة، ثم اضغط هذا الاختصار: يقرأ الرابط من الحافظة، ويطلب منك اختيار أو إنشاء المجموعة ثم الفئة، ثم يفتح نافذة إضافة برنامج بالرابط معبأً تلقائياً لتكتب الاسم والملاحظات.
Control+-: فتح قائمة العناصر المحذوفة (Blacklist) لإدارتها أو استعادتها.
Control+Shift+D: التبديل بين وضع التصميم المحلي ووضع التصميم السحابي المركزي (Online Design Mode) لمالك المستودع.
Control+D: التبديل بين وضع العرض ووضع التصميم داخل النافذة.

وضع العرض (البحث والنسخ)
اكتب في مربع البحث لتصفية الفئات والبرامج فوراً (المجموعة لا تُفلتر وتبقى ظاهرة كاملة). يُعلن الناطق بعدد النتائج بعد كل حرف.
التنقل بالسهم في قائمة المجموعة يحدد المجموعة فوراً ويملأ قائمة الفئات.
اختيار فئة يملأ قائمة البرامج الخاصة بها.
التنقل بالسهم على برنامج يقرأ ملاحظاته صوتياً تلقائياً إن وُجدت (الملاحظات لا تُنسخ أبداً).
Enter على برنامج محدد: نسخ اسمه ورابطه (والرابط الإضافي إن وُجد) للحافظة، ثم إغلاق النافذة.
Control+Enter على برنامج محدد: فتح رابطه في المتصفح دون إغلاق النافذة.
Enter داخل مربع البحث نفسه: تنظيف النص المكتوب فقط مع إبقاء النتائج الحالية ظاهرة.
زر نسخ الرابط: نسخ برنامج دون إغلاق النافذة، ويسمح بتجميع أكثر من رابط (يتحول نصه إلى "إضافة إلى النسخ" بعد أول استخدام).
Escape أو زر إغلاق: إغلاق النافذة.

وضع التصميم (إدارة البيانات)
Control+N: إضافة مجموعة جديدة.
Control+Shift+N: إضافة فئة للمجموعة المحددة حالياً.
Control+F2: إضافة برنامج للفئة المحددة حالياً (الاسم، ثم الرابط الأساسي وهو إلزامي، ثم رابط إضافي اختياري، ثم الملاحظات).
F2: تعديل العنصر الذي عليه التركيز حالياً (مجموعة أو فئة أو برنامج)، بكل بياناته.
Delete: حذف العنصر الذي عليه التركيز حالياً، مع رسالة تأكيد.
Control+M: نقل أو دمج العنصر الذي عليه التركيز حالياً (مجموعة أو فئة أو برنامج) إلى مكان آخر، مع رسالة تأكيد قبل التنفيذ.
Control+Shift+O: تفعيل المشاركة السحابية للمجموعة أو الفئة المحددة حالياً.
Control+Shift+F: إيقاف المشاركة السحابية للمجموعة أو الفئة المحددة حالياً.
Control+O أو زر استيراد بيانات (آخر عنصر في ترتيب Tab): استيراد بيانات من ملف data.json آخر ودمجها مع بياناتك الحالية دون حذف أي شيء. العنصر المطابق تماماً (نفس المسار ونفس الرابط) يُتجاهل، والعنصر بنفس المسار لكن برابط مختلف يُضاف كنسخة منفصلة بجانب القديم.

إعدادات الإضافة
من إعدادات NVDA، فئة Qadreen: تحديد لغة واجهة الإضافة (اتباع لغة NVDA، أو عربي دائماً، أو إنجليزي دائماً)، وزر للتواصل مع المطور عبر البريد الإلكتروني.""",
	"en": """Qadreen add-on help

Global shortcut
Insert+Control+Q: Open the add-on window, always opens in View mode.
Insert+Control+H: Open this help window.
Insert+Shift+C: Quick-add from any other program (browser, Telegram, WhatsApp). First copy the link as you normally would, then press this shortcut: it reads the link from the clipboard, asks you to choose or create the group then the category, then opens the add-software window with the link already filled in so you just type the name and notes.
Control+-: Open the deleted items list (Blacklist) to manage or restore them.
Control+Shift+D: Toggle between local Design mode and Central Online Design Mode for the repository owner.
Control+D: Toggle between View mode and Design mode inside the window.

View mode (search and copy)
Type in the search box to filter categories and software instantly (the Group list is not filtered and stays fully visible). The screen reader announces the result count after every keystroke.
Arrow navigation in the Group list selects a group immediately and fills the Category list.
Selecting a category fills its Software list.
Arrow navigation on a software item automatically reads its notes aloud if any exist (notes are never copied).
Enter on a selected software item: copies its name and link (and additional link if present) to the clipboard, then closes the window.
Control+Enter on a selected software item: opens its link in the browser without closing the window.
Enter inside the search box itself: clears the typed text only, keeping the current results visible.
Copy link button: copies a software item without closing the window, and allows accumulating more than one link (its label changes to "Add to copy" after first use).
Escape or the Close button: closes the window.

Design mode (data management)
Control+N: add a new group.
Control+Shift+N: add a category to the currently selected group.
Control+F2: add a software item to the currently selected category (name, then a required main link, then an optional additional link, then notes).
F2: edit the currently focused item (group, category, or software), including all its data.
Delete: delete the currently focused item, with a confirmation prompt.
Control+M: move or merge the currently focused item (group, category, or software) to another location, with a confirmation prompt before it happens.
Control+Shift+O: enable cloud sharing for the currently focused group or category.
Control+Shift+F: disable cloud sharing for the currently focused group or category.
Control+O or the Import data button (last item in Tab order): import data from another data.json file and merge it with your current data without deleting anything. An item that matches exactly (same path and same link) is skipped, and an item with the same path but a different link is added as a separate copy next to the old one.

Add-on settings
From NVDA Settings, under the Qadreen category: choose the add-on's interface language (follow NVDA's language, always Arabic, or always English), and a button to contact the developer by email.""",
}


def tr(key, *args):
	"""إرجاع النص المترجم المناسب للغة الحالية، مع دعم .format إن وُجدت وسائط"""
	entry = STRINGS.get(key)
	if entry is None:
		return key
	text = entry.get(getLanguage(), entry.get("en", key))
	if args:
		return text.format(*args)
	return text


def formatResultsCount(count):
	"""إعلان صوتي بعدد نتائج البحث، بصياغة عربية صحيحة نحوياً حسب العدد"""
	if getLanguage() == "ar":
		if count == 0:
			return "لا توجد نتائج"
		if count == 1:
			return "نتيجة واحدة"
		if count == 2:
			return "نتيجتان"
		if 3 <= count <= 10:
			return "{} نتائج".format(count)
		return "{} نتيجة".format(count)
	else:
		return "1 result" if count == 1 else "{} results".format(count)


# =====================================================================
# تسجيل مواصفات الإعداد (confspec) الخاصة بالإضافة
# =====================================================================

confspec = {
	"language": 'option("follow","ar","en", default="follow")',
	"onlineMode": "boolean(default=false)",   # Default is offline
	"gistId": 'string(default="")',
	"pat": 'string(default="")',              # Stored as plain text
	# Repository source settings. Gist settings above remain supported.
	"sourceType": 'option("gist","repo", default="gist")',
	"repoOwnerName": 'string(default="")',
	"repoPath": 'string(default="qadreen_data.json")',
	"repoBranch": 'string(default="main")',
	"repoPat": 'string(default="")',
}
config.conf.spec["qadreen"] = confspec


# قفل واحد مشترك يحمي أي قراءة أو كتابة لملف البيانات لضمان Thread-Safety
dataFileLock = threading.Lock()


def loadData():
	"""تحميل بيانات Qadreen."""
	with dataFileLock:
		if os.path.isfile(DATA_FILE):
			try:
				with open(DATA_FILE, "r", encoding="utf-8") as f:
					return json.load(f)
			except (OSError, json.JSONDecodeError):
				return {}
		return {}


def saveData(data):
	"""حفظ بيانات Qadreen."""
	with dataFileLock:
		try:
			with open(DATA_FILE, "w", encoding="utf-8") as f:
				json.dump(data, f, ensure_ascii=False, indent="\t")
			return True
		except OSError:
			return False


METADATA_KEY = "__metadata__"


def getGroupNames(data):
	"""أسماء المجموعات الحقيقية فقط، مع استثناء مفتاح البيانات الوصفية المحجوز"""
	return sorted(name for name in data.keys() if name != METADATA_KEY)


def getSharedItems(data):
	return data.get(METADATA_KEY, {}).get("shared_items", [])


def isPathShared(data, groupName, categoryName=None):
	sharedItems = getSharedItems(data)
	if [groupName] in sharedItems:
		return True
	if categoryName is not None and [groupName, categoryName] in sharedItems:
		return True
	return False


def addSharedPath(data, path):
	metadata = data.setdefault(METADATA_KEY, {})
	sharedItems = metadata.setdefault("shared_items", [])
	if path not in sharedItems:
		sharedItems.append(path)


def removeSharedPath(data, path):
	sharedItems = getSharedItems(data)
	if path in sharedItems:
		sharedItems.remove(path)


def getLocalIgnored(data):
	"""الحصول على قائمة السجلات المحذوفة محلياً من __metadata__."""
	metadata = data.setdefault(METADATA_KEY, {})
	return metadata.setdefault("local_ignored_urls", [])


def getCloudDeleted(data):
	"""الحصول على قائمة السجلات المحذوفة مركزياً (Tombstones) من __metadata__."""
	metadata = data.setdefault(METADATA_KEY, {})
	return metadata.setdefault("cloud_deleted_urls", [])


def addLocalIgnored(data, url, name, group="", category=""):
	"""إضافة برنامج إلى قائمة الحذف المحلي ومنع التكرار بناءً على url."""
	cleanUrl = url.strip()
	if not cleanUrl:
		return
	items = getLocalIgnored(data)
	for item in items:
		if item.get("url") == cleanUrl:
			item["name"] = name
			item["group"] = group
			item["category"] = category
			return
	items.append({
		"url": cleanUrl,
		"name": name,
		"group": group,
		"category": category
	})


def addCloudDeleted(data, url, name, group="", category=""):
	"""إضافة برنامج إلى قائمة الحذف المركزي السحابي ومنع التكرار بناءً على url."""
	cleanUrl = url.strip()
	if not cleanUrl:
		return
	items = getCloudDeleted(data)
	for item in items:
		if item.get("url") == cleanUrl:
			item["name"] = name
			item["group"] = group
			item["category"] = category
			return
	items.append({
		"url": cleanUrl,
		"name": name,
		"group": group,
		"category": category
	})


def removeLocalIgnored(data, url):
	"""إزالة برنامج من قائمة الحذف المحلي بناءً على url."""
	cleanUrl = url.strip()
	if not cleanUrl:
		return
	items = getLocalIgnored(data)
	items[:] = [item for item in items if item.get("url") != cleanUrl]


def removeCloudDeleted(data, url):
	"""إزالة برنامج من قائمة الحذف السحابي بناءً على url."""
	cleanUrl = url.strip()
	if not cleanUrl:
		return
	items = getCloudDeleted(data)
	items[:] = [item for item in items if item.get("url") != cleanUrl]


# =====================================================================
# فحص التحديثات: مرة واحدة فقط عند كل بدء تشغيل لـNVDA، يتحقق من أحدث
# إصدار مستقر منشور على GitHub (وليس أي نسخة تجريبية أو مسودة، لأن نقطة
# نهاية "أحدث إصدار" في GitHub تستثني هذه النسخ تلقائياً)
# =====================================================================

GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/saedmohamedn2210-create/Qadreen/releases/latest"

def parseVersion(versionString):
	"""تحويل نص إصدار مثل '1.2' أو 'v1.2' إلى tuple أرقام لمقارنة صحيحة"""
	parts = []
	for part in versionString.strip().lstrip("vV").split("."):
		digits = "".join(ch for ch in part if ch.isdigit())
		parts.append(int(digits) if digits else 0)
	return tuple(parts)


def promptRestart():
	"""تُعرض بعد اكتمال التثبيت: تسأل المستخدم إن كان يريد إعادة تشغيل
	NVDA الآن لتفعيل النسخة الجديدة. تُستدعى دائماً عبر wx.CallAfter من
	الخيط الرئيسي، وتستخدم gui.mainFrame مع prePopup/postPopup كما يتطلب
	NVDA لأي نافذة modal تُعرض من سياق خارج نافذة مفتوحة فعلاً للإضافة."""
	gui.mainFrame.prePopup()
	try:
		restartNow = confirmYesNo(
			gui.mainFrame,
			tr("updateInstalledTitle"),
			tr("msgUpdateInstalledRestart")
		)
	finally:
		gui.mainFrame.postPopup()
	if restartNow:
		import core
		core.restart()


def downloadAndInstallUpdate(releaseData):
	"""تعمل داخل خيط منفصل: تنزيل حزمة التحديث، نسخ بيانات المستخدم
	الحالية احتياطياً، تثبيت الحزمة الجديدة، ثم عرض طلب إعادة التشغيل."""
	asset = None
	for a in releaseData.get("assets", []):
		if a.get("name", "").endswith(".nvda-addon"):
			asset = a
			break
	if asset is None:
		wx.CallAfter(ui.message, tr("msgUpdateAssetNotFound"))
		return

	tempPath = os.path.join(tempfile.gettempdir(), "Qadreen_update.nvda-addon")
	try:
		request = urllib.request.Request(
			asset["browser_download_url"],
			headers={"User-Agent": "Qadreen-NVDA-Addon"}
		)
		with urllib.request.urlopen(request, timeout=60) as response:
			fileData = response.read()
		with open(tempPath, "wb") as outFile:
			outFile.write(fileData)
	except Exception:
		wx.CallAfter(ui.message, tr("msgUpdateDownloadFailed"))
		return

	# التثبيت الفعلي يجب أن يتم على الخيط الرئيسي لـNVDA وليس هذا الخيط
	# الخلفي، وإلا قد يفشل تثبيت الإضافة بصمت أو يفسد حالة التثبيت المعلّق
	wx.CallAfter(installUpdateOnMainThread, tempPath)


def installUpdateOnMainThread(tempPath):
	"""تُنفَّذ على الخيط الرئيسي حصراً عبر wx.CallAfter"""
	try:
		# 1. فتح حزمة التحديث المُنزلة والتحقق من ملفاتها
		bundle = addonHandler.AddonBundle(tempPath)
		# 2. استخراج الحزمة إلى مجلد Qadreen.pendingInstall (لا يتعارض
		#    مع مجلد Qadreen النشط، لأن الاسم مختلف تماماً)
		addonHandler.installAddonBundle(bundle)
		# 3. وصلنا هنا فقط لو نجح الاستخراج بالكامل. الآن، وليس قبل
		#    ذلك، نُعلِّم النسخة القديمة النشطة للحذف عند الإقلاع القادم،
		#    حتى يجد NVDA المسار فارغاً وينقل pendingInstall مكانه بسلاسة
		curAddon = addonHandler.getCodeAddon()
		if curAddon and not getattr(curAddon, "isPendingRemove", False):
			curAddon.requestRemove()
	except Exception as e:
		# لو فشلت الخطوة 1 أو 2: لن نصل أبداً لسطر requestRemove، فتبقى
		# النسخة القديمة سليمة وتعمل كما هي دون أي أثر
		log.error("Failed to install Qadreen update bundle: {}".format(e), exc_info=True)
		ui.message(tr("msgUpdateInstallFailed"))
		return
	# 4. نجح كل شيء: نطلب إعادة التشغيل
	promptRestart()


def onUpdateFound(releaseData, latestTag):
	"""تُستدعى عبر wx.CallAfter من خيط الفحص: تعرض تأكيداً بسيطاً (نعم/لا)
	على المستخدم، وعند الموافقة فقط يبدأ التنزيل والتثبيت تلقائياً."""
	gui.mainFrame.prePopup()
	try:
		proceed = confirmYesNo(
			gui.mainFrame,
			tr("updateAvailableTitle"),
			tr("msgUpdateConfirm", latestTag)
		)
	finally:
		gui.mainFrame.postPopup()
	if proceed:
		threading.Thread(target=downloadAndInstallUpdate, args=(releaseData,), daemon=True).start()


def checkForUpdateInBackground():
	"""تعمل داخل خيط منفصل حتى لا تُجمّد NVDA أثناء انتظار الاتصال بالشبكة"""
	try:
		# تأخير بسيط حتى لا تتزاحم الرسالة الصوتية مع إعلانات بدء تشغيل NVDA
		time.sleep(8)

		try:
			addon = addonHandler.getCodeAddon()
			currentVersion = addon.manifest["version"]
		except Exception:
			return

		request = urllib.request.Request(
			GITHUB_LATEST_RELEASE_API,
			headers={"Accept": "application/vnd.github+json", "User-Agent": "Qadreen-NVDA-Addon"}
		)
		with urllib.request.urlopen(request, timeout=10) as response:
			releaseData = json.loads(response.read().decode("utf-8"))

		latestTag = releaseData.get("tag_name", "")
		if not latestTag:
			return

		if parseVersion(latestTag) > parseVersion(currentVersion):
			wx.CallAfter(onUpdateFound, releaseData, latestTag)
	except Exception:
		# فشل الاتصال بالشبكة أو أي خطأ آخر: نتجاهله بصمت تماماً، حتى لا
		# نزعج المستخدم برسائل خطأ عند غياب الإنترنت مثلاً
		pass


def mergeData(target, source):
	"""
	دمج البيانات المستوردة داخل البيانات الحالية دون حذف أو استبدال.
	الرابط الأساسي url هو المعيار الحاسم والوحيد لتحديد التعارض:
	- يُرفض أي برنامج يطابق رابطه الأساسي أي رابط أساسي موجود مسبقاً.
	- لا تُنشأ مجموعة أو فئة جديدة إذا تم رفض العنصر بسبب تطابق الرابط.
	- إذا اختلف الرابط الأساسي وتكرر الاسم، يُضاف كنسخة مستقلة: Name (2), Name (3)...
	"""
	addedCount = 0
	duplicatedCount = 0

	# جمع كافة الروابط الأساسية الموجودة حالياً في البيانات
	existingUrls = set()
	for groupData in target.values():
		if not isinstance(groupData, dict):
			continue
		for categoryData in groupData.values():
			if not isinstance(categoryData, dict):
				continue
			for info in categoryData.values():
				if not isinstance(info, dict):
					continue
				url = info.get("url", "")
				if url:
					existingUrls.add(url)

	for groupName, categories in source.items():
		if not isinstance(categories, dict):
			continue
		for categoryName, softwareDict in categories.items():
			if not isinstance(softwareDict, dict):
				continue
			for softwareName, info in softwareDict.items():
				if not isinstance(info, dict):
					continue

				importedUrl = info.get("url", "")
				if not importedUrl or importedUrl in existingUrls:
					continue

				# لا ننشئ المجموعة والفئة إلا بعد التأكد التام من قبول العنصر
				targetGroup = target.setdefault(groupName, {})
				targetCategory = targetGroup.setdefault(categoryName, {})

				if softwareName not in targetCategory:
					targetCategory[softwareName] = info
					addedCount += 1
				else:
					counter = 2
					newName = "{} ({})".format(softwareName, counter)
					while newName in targetCategory:
						counter += 1
						newName = "{} ({})".format(softwareName, counter)
					targetCategory[newName] = info
					duplicatedCount += 1

				existingUrls.add(importedUrl)

	return addedCount, duplicatedCount


def isUrlExists(data, targetUrl, exclude=None):
	"""
	فحص ما إذا كان الرابط الأساسي targetUrl موجوداً في أي مكان داخل البيانات.
	exclude: tuple اختياري بصيغة (groupName, categoryName, softwareName)
	لاستثنائه أثناء التعديل أو النقل حتى لا يعتبر العنصر نفسه تعارضاً.
	"""
	if not targetUrl:
		return False
	targetUrlClean = targetUrl.strip()
	if not targetUrlClean:
		return False

	for groupName, categories in data.items():
		if groupName == METADATA_KEY or not isinstance(categories, dict):
			continue
		for categoryName, softwareDict in categories.items():
			if not isinstance(softwareDict, dict):
				continue
			for softwareName, info in softwareDict.items():
				if not isinstance(info, dict):
					continue
				if exclude and (groupName, categoryName, softwareName) == exclude:
					continue
				existingUrl = info.get("url", "").strip()
				if existingUrl and existingUrl == targetUrlClean:
					return True
	return False


def getUniqueSoftwareName(categoryDict, baseName):
	"""
	توليد اسم فريد للبرنامج داخل الفئة المحددة لتجنب استبدال البرامج ذات الروابط المختلفة.
	إذا كان الاسم غير موجود يُعاد كما هو.
	إذا كان موجوداً، يُضاف ترقيم تسلسلي: Name (2), Name (3)...
	"""
	if baseName not in categoryDict:
		return baseName
	counter = 2
	newName = "{} ({})".format(baseName, counter)
	while newName in categoryDict:
		counter += 1
		newName = "{} ({})".format(baseName, counter)
	return newName


def confirmYesNo(parent, title, message):
	"""نافذة تأكيد عامة (نعم/لا)، الافتراضي هو (لا) للسلامة"""
	dlg = wx.MessageDialog(
		parent,
		message,
		title,
		style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
	)
	result = dlg.ShowModal() == wx.ID_YES
	dlg.Destroy()
	return result


def mergeDict(target, source):
	"""دمج قاموس مصدر داخل قاموس هدف بشكل متكرر. عند تعارض المفاتيح في أعمق
	مستوى (رابط/ملاحظات)، تُستبدل قيمة الهدف بقيمة المصدر."""
	for key, value in source.items():
		if key in target and isinstance(target[key], dict) and isinstance(value, dict):
			mergeDict(target[key], value)
		else:
			target[key] = value


class SimpleNameDialog(wx.Dialog):
	"""نافذة إدخال بسيطة تحتوي حقل نصي واحد فقط (اسم المجموعة أو الفئة)"""

	def __init__(self, parent, title, fieldLabel, initialValue=""):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)

		sizer = wx.BoxSizer(wx.VERTICAL)

		label = wx.StaticText(self, label=fieldLabel)
		self.nameCtrl = wx.TextCtrl(self, value=initialValue)
		self.nameCtrl.SetName(fieldLabel)

		buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

		sizer.Add(label, 0, wx.ALL, 8)
		sizer.Add(self.nameCtrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizerAndFit(sizer)
		self.nameCtrl.SetFocus()
		self.nameCtrl.SelectAll()

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)

	def onOK(self, event):
		if not self.nameCtrl.GetValue().strip():
			ui.message(tr("msgNameRequired"))
			self.nameCtrl.SetFocus()
			return
		event.Skip()

	def GetValueEntered(self):
		return self.nameCtrl.GetValue().strip()


class SoftwareDialog(wx.Dialog):
	"""نافذة إضافة أو تعديل برنامج: الاسم، الرابط الأساسي، رابط إضافي اختياري، الملاحظات"""

	def __init__(self, parent, title, name="", url="", url2="", notes=""):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)

		sizer = wx.BoxSizer(wx.VERTICAL)

		nameLabel = wx.StaticText(self, label=tr("softwareNameLabel"))
		self.nameCtrl = wx.TextCtrl(self, value=name)
		self.nameCtrl.SetName(tr("softwareNameLabel"))

		urlLabel = wx.StaticText(self, label=tr("urlLabel"))
		self.urlCtrl = wx.TextCtrl(self, value=url)
		self.urlCtrl.SetName(tr("urlLabel"))

		url2Label = wx.StaticText(self, label=tr("url2Label"))
		self.url2Ctrl = wx.TextCtrl(self, value=url2)
		self.url2Ctrl.SetName(tr("url2Label"))

		notesLabel = wx.StaticText(self, label=tr("notesLabel"))
		self.notesCtrl = wx.TextCtrl(self, value=notes)
		self.notesCtrl.SetName(tr("notesLabel"))

		buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

		for lbl, ctrl in (
			(nameLabel, self.nameCtrl),
			(urlLabel, self.urlCtrl),
			(url2Label, self.url2Ctrl),
			(notesLabel, self.notesCtrl),
		):
			sizer.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
			sizer.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizerAndFit(sizer)
		self.nameCtrl.SetFocus()
		self.nameCtrl.SelectAll()

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)

	def onOK(self, event):
		if not self.nameCtrl.GetValue().strip():
			ui.message(tr("msgSoftwareNameRequired"))
			self.nameCtrl.SetFocus()
			return
		if not self.urlCtrl.GetValue().strip():
			ui.message(tr("msgUrlRequired"))
			self.urlCtrl.SetFocus()
			return
		event.Skip()

	def GetValuesEntered(self):
		return (
			self.nameCtrl.GetValue().strip(),
			self.urlCtrl.GetValue().strip(),
			self.url2Ctrl.GetValue().strip(),
			self.notesCtrl.GetValue().strip(),
		)


class ChoiceDialog(wx.Dialog):
	"""نافذة اختيار عنصر واحد من قائمة (تُستخدم لاختيار وجهة النقل)"""

	def __init__(self, parent, title, label, choices):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		sizer = wx.BoxSizer(wx.VERTICAL)

		lbl = wx.StaticText(self, label=label)
		self.listBox = wx.ListBox(self, choices=choices, style=wx.LB_SINGLE)
		self.listBox.SetName(label)
		if choices:
			self.listBox.SetSelection(0)

		buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

		sizer.Add(lbl, 0, wx.ALL, 8)
		sizer.Add(self.listBox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizerAndFit(sizer)
		self.SetSize((360, 320))
		self.listBox.SetFocus()

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
		self.Bind(wx.EVT_LISTBOX_DCLICK, self.onDClick)

	def onOK(self, event):
		if self.listBox.GetSelection() == wx.NOT_FOUND:
			ui.message(tr("msgSelectItemFirst"))
			return
		event.Skip()

	def onDClick(self, event):
		self.EndModal(wx.ID_OK)

	def GetSelectedChoice(self):
		return self.listBox.GetStringSelection()


class HelpDialog(wx.Dialog):
	"""نافذة مساعدة للقراءة فقط، تعرض شرح كل الاختصارات والوظائف باللغة الحالية للإضافة"""

	def __init__(self, parent):
		super().__init__(
			parent,
			title=tr("helpDialogTitle"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)

		mainSizer = wx.BoxSizer(wx.VERTICAL)
		contentSizer = wx.BoxSizer(wx.VERTICAL)
		sizerHelper = gui.guiHelper.BoxSizerHelper(self, sizer=contentSizer)

		text = HELP_TEXT.get(getLanguage(), HELP_TEXT["en"])
		self.textCtrl = wx.TextCtrl(
			self, value=text,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP
		)
		self.textCtrl.SetName(tr("helpDialogTitle"))

		sizerHelper.addItem(self.textCtrl, proportion=1, flag=wx.EXPAND)

		buttonSizer = gui.guiHelper.ButtonHelper(wx.HORIZONTAL)
		button = buttonSizer.addButton(self, label=tr("helpCloseButton"), id=wx.ID_CLOSE)
		button.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
		sizerHelper.addDialogDismissButtons(buttonSizer)

		mainSizer.Add(
			contentSizer,
			border=gui.guiHelper.BORDER_FOR_DIALOGS,
			flag=wx.ALL | wx.EXPAND,
			proportion=1
		)
		self.SetSizer(mainSizer)

		self.SetAffirmativeId(wx.ID_CLOSE)
		self.SetEscapeId(wx.ID_CLOSE)

		self.SetSize((640, 520))
		self.CentreOnScreen()

		wx.CallAfter(self.textCtrl.SetFocus)


class DeletedItemsDialog(wx.Dialog):
	"""نافذة إدارة العناصر المحذوفة (Blacklist) الخاصة بإضافة قادرين"""

	def __init__(self, parent, data, plugin):
		super().__init__(
			parent,
			title=tr("deletedItemsDialogTitle"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)
		self.data = data
		self.plugin = plugin
		self.itemsList = []

		sizer = wx.BoxSizer(wx.VERTICAL)
		lbl = wx.StaticText(self, label=tr("deletedItemsListLabel"))
		self.listBox = wx.ListBox(self, style=wx.LB_SINGLE)
		self.listBox.SetName(tr("deletedItemsListLabel"))

		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.removeButton = wx.Button(self, label=tr("removeBlacklistButton"))
		self.closeButton = wx.Button(self, id=wx.ID_CLOSE, label=tr("closeButton"))
		buttonsSizer.Add(self.removeButton, 0, wx.RIGHT, 8)
		buttonsSizer.Add(self.closeButton, 0)

		sizer.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		sizer.Add(self.listBox, 1, wx.EXPAND | wx.ALL, 8)
		sizer.Add(buttonsSizer, 0, wx.ALIGN_CENTER | wx.ALL, 8)

		self.SetSizer(sizer)
		self.SetSize((480, 360))
		self.CentreOnScreen()

		self._populateItems()

		self.removeButton.Bind(wx.EVT_BUTTON, self.onRemoveFromBlacklist)
		self.closeButton.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

		wx.CallAfter(self.listBox.SetFocus)

	def _populateItems(self):
		self.listBox.Clear()
		self.itemsList = []

		localIgnored = getLocalIgnored(self.data)
		cloudDeleted = getCloudDeleted(self.data)

		# عناصر الحذف المحلي تظهر لجميع المستخدمين
		for item in localIgnored:
			displayStr = "{} — {}".format(item.get("name", ""), tr("labelLocal"))
			self.itemsList.append(("local", item.get("url", ""), item))
			self.listBox.Append(displayStr)

		# عناصر الحذف السحابي تظهر حصراً للمالك
		if getattr(self.plugin, "isRepoOwner", False):
			for item in cloudDeleted:
				displayStr = "{} — {}".format(item.get("name", ""), tr("labelCloud"))
				self.itemsList.append(("cloud", item.get("url", ""), item))
				self.listBox.Append(displayStr)

		if self.itemsList:
			self.listBox.SetSelection(0)
		else:
			ui.message(tr("msgNoDeletedItems"))

	def onRemoveFromBlacklist(self, event=None):
		sel = self.listBox.GetSelection()
		if sel == wx.NOT_FOUND or sel >= len(self.itemsList):
			ui.message(tr("msgSelectItemFirst"))
			return

		itemType, url, record = self.itemsList[sel]
		if itemType == "local":
			removeLocalIgnored(self.data, url)
		elif itemType == "cloud":
			removeCloudDeleted(self.data, url)

		saveData(self.data)
		ui.message(tr("msgItemRemovedFromBlacklist"))

		self._populateItems()
		newCount = len(self.itemsList)
		if newCount > 0:
			newSel = min(sel, newCount - 1)
			self.listBox.SetSelection(newSel)
			self.listBox.SetFocus()

	def onCharHook(self, event):
		keyCode = event.GetKeyCode()
		if keyCode == wx.WXK_ESCAPE:
			self.Close()
			return
		if keyCode == wx.WXK_DELETE:
			self.onRemoveFromBlacklist()
			return
		event.Skip()


class SearchDialog(wx.Dialog):
	"""النافذة الرئيسية للإضافة: وضع العرض (بحث ونسخ) ووضع التصميم (إدارة بيانات)"""

	def __init__(self, parent, data, startMode="view", plugin=None):
		super().__init__(
			parent,
			title=tr("dialogTitleDesign") if startMode == "design" else tr("dialogTitleView"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)
		self.data = data
		self.plugin = plugin
		# قائمة الروابط المجمعة للنسخ المتعدد: كل عنصر (اسم البرنامج، الرابط)
		self.copiedItems = []
		self._notesTimer = None
		# الوضع الحالي: "view" وضع العرض، أو "design" وضع التصميم
		self.mode = startMode

		self._buildUI()
		self._bindEvents()
		self._populateGroups()

		if self.mode == "design":
			# نُنشئ النافذة مباشرة في وضع التصميم (تُستخدم مع الإضافة
			# السريعة من الحافظة)، بدون المرور بوضع العرض أولاً وبدون
			# إعلان "وضع التصميم" الذي يوحي بدخول عام للتصفح
			self.searchLabel.Hide()
			self.searchCtrl.Hide()
			self.copyButton.Hide()
			self.importButton.Show()

		self.SetSize((560, 420))
		self.CentreOnScreen()

	# ---------------------------------------------------------------
	# بناء الواجهة
	# ---------------------------------------------------------------

	def _buildUI(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)

		self.searchLabel = wx.StaticText(self, label=tr("searchLabel"))
		self.searchCtrl = wx.TextCtrl(self)
		self.searchCtrl.SetName(tr("searchCtrlName"))

		listsSizer = wx.BoxSizer(wx.HORIZONTAL)

		groupSizer = wx.BoxSizer(wx.VERTICAL)
		groupLabel = wx.StaticText(self, label=tr("groupLabel"))
		self.groupList = wx.ListBox(self, style=wx.LB_SINGLE)
		self.groupList.SetName(tr("groupListName"))
		groupSizer.Add(groupLabel, 0, wx.BOTTOM, 4)
		groupSizer.Add(self.groupList, 1, wx.EXPAND)

		categorySizer = wx.BoxSizer(wx.VERTICAL)
		categoryLabel = wx.StaticText(self, label=tr("categoryLabel"))
		self.categoryList = wx.ListBox(self, style=wx.LB_SINGLE)
		self.categoryList.SetName(tr("categoryListName"))
		categorySizer.Add(categoryLabel, 0, wx.BOTTOM, 4)
		categorySizer.Add(self.categoryList, 1, wx.EXPAND)

		softwareSizer = wx.BoxSizer(wx.VERTICAL)
		softwareLabel = wx.StaticText(self, label=tr("softwareLabel"))
		self.softwareList = wx.ListBox(self, style=wx.LB_SINGLE)
		self.softwareList.SetName(tr("softwareListName"))
		softwareSizer.Add(softwareLabel, 0, wx.BOTTOM, 4)
		softwareSizer.Add(self.softwareList, 1, wx.EXPAND)

		listsSizer.Add(groupSizer, 1, wx.EXPAND | wx.RIGHT, 6)
		listsSizer.Add(categorySizer, 1, wx.EXPAND | wx.RIGHT, 6)
		listsSizer.Add(softwareSizer, 1, wx.EXPAND)

		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.copyButton = wx.Button(self, label=tr("copyButton"))
		self.closeButton = wx.Button(self, label=tr("closeButton"))
		self.importButton = wx.Button(self, label=tr("importButton"))
		self.importButton.Hide()
		buttonsSizer.Add(self.copyButton, 0, wx.RIGHT, 8)
		buttonsSizer.Add(self.closeButton, 0, wx.RIGHT, 8)
		buttonsSizer.Add(self.importButton, 0)

		mainSizer.Add(self.searchLabel, 0, wx.LEFT | wx.TOP, 8)
		mainSizer.Add(self.searchCtrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
		mainSizer.Add(listsSizer, 1, wx.EXPAND | wx.ALL, 8)
		mainSizer.Add(buttonsSizer, 0, wx.ALIGN_LEFT | wx.LEFT | wx.BOTTOM, 8)

		self.SetSizer(mainSizer)

	def _bindEvents(self):
		self.searchCtrl.Bind(wx.EVT_TEXT, self.onSearchTextChanged)
		self.groupList.Bind(wx.EVT_LISTBOX, self.onGroupSelected)
		self.categoryList.Bind(wx.EVT_LISTBOX, self.onCategorySelected)
		self.softwareList.Bind(wx.EVT_LISTBOX, self.onSoftwareSelected)
		self.softwareList.Bind(wx.EVT_KEY_DOWN, self.onSoftwareKeyDown)
		self.copyButton.Bind(wx.EVT_BUTTON, self.onCopyButton)
		self.closeButton.Bind(wx.EVT_BUTTON, lambda evt: self.Close())
		self.importButton.Bind(wx.EVT_BUTTON, lambda evt: self._importData())
		self.Bind(wx.EVT_CHAR_HOOK, self.onCharHook)

	# ---------------------------------------------------------------
	# تعبئة القوائم - وضع التصفح العادي (بدون بحث)
	# ---------------------------------------------------------------

	def _populateGroups(self):
		self.groupList.Clear()
		for groupName in getGroupNames(self.data):
			self.groupList.Append(groupName)
		self.categoryList.Clear()
		self.softwareList.Clear()

	def _populateCategoriesForGroup(self, groupName):
		self.categoryList.Clear()
		self.softwareList.Clear()
		categories = self.data.get(groupName, {})
		for categoryName in sorted(categories.keys()):
			self.categoryList.Append(categoryName, (groupName, categoryName))

	def _populateSoftwareForCategory(self, groupName, categoryName):
		self.softwareList.Clear()
		software = self.data.get(groupName, {}).get(categoryName, {})
		for softwareName in sorted(software.keys()):
			self.softwareList.Append(softwareName, (groupName, categoryName, softwareName))

	# ---------------------------------------------------------------
	# تعبئة القوائم - وضع البحث (يشمل الفئات والبرامج، يستثني المجموعة)
	# ---------------------------------------------------------------

	def _populateFromSearch(self, query):
		self.categoryList.Clear()
		self.softwareList.Clear()

		addedCategories = set()
		# نجمع كل النتائج أولاً، ثم نرتبها أبجدياً قبل عرضها
		categoryEntries = []  # (categoryLabel, key)
		softwareEntries = []  # (softwareLabel, clientData)

		for groupName in getGroupNames(self.data):
			categories = self.data[groupName]
			for categoryName in sorted(categories.keys()):
				softwareDict = categories[categoryName]
				categoryMatches = query in categoryName.lower()
				matchedSoftware = sorted(
					name for name in softwareDict.keys()
					if query in name.lower() or categoryMatches
				)
				if matchedSoftware:
					key = (groupName, categoryName)
					categoryLabel = "{} ({})".format(categoryName, groupName)
					if key not in addedCategories:
						categoryEntries.append((categoryLabel, key))
						addedCategories.add(key)
					for softwareName in matchedSoftware:
						# نُضيف المجموعة والفئة لاسم البرنامج الظاهر في نتائج
						# البحث، لأن نفس اسم البرنامج قد يتكرر في أكثر من
						# مجموعة (مثال: Firefox في Android وiPhone معاً)
						softwareLabel = "{} — {} / {}".format(softwareName, groupName, categoryName)
						softwareEntries.append((softwareLabel, (groupName, categoryName, softwareName)))

		for categoryLabel, key in sorted(categoryEntries, key=lambda item: item[0]):
			self.categoryList.Append(categoryLabel, key)
		for softwareLabel, clientData in sorted(softwareEntries, key=lambda item: item[0]):
			self.softwareList.Append(softwareLabel, clientData)

	# ---------------------------------------------------------------
	# الأحداث العامة
	# ---------------------------------------------------------------

	def onSearchTextChanged(self, event):
		if self.mode == "design":
			return
		query = self.searchCtrl.GetValue().strip().lower()
		if not query:
			self._populateGroups()
		else:
			self._populateFromSearch(query)
			count = self.softwareList.GetCount()
			ui.message(formatResultsCount(count))

	def onGroupSelected(self, event):
		groupName = self.groupList.GetStringSelection()
		if groupName:
			self._populateCategoriesForGroup(groupName)

	def onCategorySelected(self, event):
		index = self.categoryList.GetSelection()
		if index == wx.NOT_FOUND:
			return
		groupCategoryData = self.categoryList.GetClientData(index)
		if not groupCategoryData:
			return
		groupName, categoryName = groupCategoryData

		# إن كنا في وضع البحث، لا نعيد تعبئة قائمة البرامج بكل عناصر
		# الفئة، بل نُبقي فقط على العناصر المطابقة الظاهرة أصلاً.
		if not self.searchCtrl.GetValue().strip():
			self._populateSoftwareForCategory(groupName, categoryName)
			# مزامنة تحديد المجموعة في قائمة Group
			groupIndex = self.groupList.FindString(groupName)
			if groupIndex != wx.NOT_FOUND:
				self.groupList.SetSelection(groupIndex)

	def onSoftwareSelected(self, event):
		# نقرأ الملاحظات صوتياً فقط في وضع العرض، ولا نستخدمها أبداً عند النسخ
		if self._notesTimer is not None:
			self._notesTimer.Stop()
			self._notesTimer = None

		if self.mode != "view":
			return
		index = self.softwareList.GetSelection()
		if index == wx.NOT_FOUND:
			return
		clientData = self.softwareList.GetClientData(index)
		if not clientData:
			return
		groupName, categoryName, softwareName = clientData
		info = self.data.get(groupName, {}).get(categoryName, {}).get(softwareName, {})
		notes = info.get("notes", "").strip()
		if notes:
			# تأخير حقيقي (200 ملي ثانية) قبل نطق الملاحظات، حتى يكتمل
			# إعلان NVDA الطبيعي لاسم العنصر أولاً. CallAfter وحدها لم
			# تكن كافية لأنها فقط تنتظر دورة الأحداث التالية، وقد تسبق
			# إعلان NVDA الفعلي. نُلغي أي مؤقت سابق لم يُنفَّذ بعد حتى لا
			# تُقرأ ملاحظات عنصر سابق أثناء التنقل السريع بالأسهم.
			self._notesTimer = wx.CallLater(200, ui.message, notes)

	def onSoftwareKeyDown(self, event):
		# لم يعد الاعتماد على هذا المعالج لمفتاح Enter، لأن نافذة الحوار
		# تعترضه قبل وصوله هنا (انظر onCharHook). أُبقيه لأي مفاتيح أخرى مستقبلية.
		event.Skip()

	def onCharHook(self, event):
		keyCode = event.GetKeyCode()

		if keyCode == wx.WXK_ESCAPE:
			self.Close()
			return

		if event.ControlDown() and not event.ShiftDown() and keyCode == ord("D"):
			self._toggleMode()
			return

		# معالجة Enter في وضع العرض هنا مباشرة، لأن نافذة الحوار تعترض
		# مفتاح Enter (بحثاً عن زر افتراضي) قبل أن يصل لقائمة البرامج
		if self.mode == "view" and self.FindFocus() == self.softwareList:
			if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
				if event.ControlDown():
					self._openSelectedLink()
				else:
					self._copySelectedAndClose()
				return

		# Enter داخل مربع البحث نفسه: تنظيف النص المكتوب فقط، مع إبقاء
		# نتائج البحث الحالية ظاهرة في Category وSoftware كما هي (نستخدم
		# ChangeValue بدل SetValue لأنها لا تُطلق حدث EVT_TEXT، فلا تُعاد
		# تعبئة القوائم بكل المجموعات من جديد)
		if self.mode == "view" and self.FindFocus() == self.searchCtrl:
			if keyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
				self.searchCtrl.ChangeValue("")
				return

		if self.mode == "design":
			if event.ControlDown() and event.ShiftDown() and keyCode == ord("O"):
				self._toggleSharing(share=True)
				return
			if event.ControlDown() and event.ShiftDown() and keyCode == ord("F"):
				self._toggleSharing(share=False)
				return
			if event.ControlDown() and event.ShiftDown() and keyCode == ord("N"):
				self._addCategory()
				return
			if event.ControlDown() and not event.ShiftDown() and keyCode == ord("N"):
				self._addGroup()
				return
			if event.ControlDown() and keyCode == wx.WXK_F2:
				self._addSoftware()
				return
			if keyCode == wx.WXK_F2:
				self._editFocusedItem()
				return
			if keyCode == wx.WXK_DELETE:
				self._deleteFocusedItem()
				return
			if event.ControlDown() and not event.ShiftDown() and keyCode == ord("O"):
				self._importData()
				return
			if event.ControlDown() and not event.ShiftDown() and keyCode == ord("M"):
				self._moveFocusedItem()
				return

		event.Skip()

	def onCopyButton(self, event):
		item = self._getSelectedSoftwareItem()
		if not item:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName, categoryName, softwareName, url, url2 = item
		self.copiedItems.append((softwareName, url, url2))
		self._writeClipboard()
		self.copyButton.SetLabel(tr("addToCopyButton"))
		ui.message(tr("msgCopied"))

	# ---------------------------------------------------------------
	# التبديل بين وضع العرض ووضع التصميم
	# ---------------------------------------------------------------

	def _toggleMode(self):
		self.searchCtrl.SetValue("")
		if self.mode == "view":
			self.mode = "design"
			self.SetTitle(tr("dialogTitleDesign"))
			self.searchLabel.Hide()
			self.searchCtrl.Hide()
			self.copyButton.Hide()
			self.importButton.Show()
			ui.message(tr("msgDesignMode"))
		else:
			self.mode = "view"
			self.SetTitle(tr("dialogTitleView"))
			self.searchLabel.Show()
			self.searchCtrl.Show()
			self.copyButton.Show()
			self.importButton.Hide()
			ui.message(tr("msgViewMode"))

		self._populateGroups()
		self.Layout()

		focusTarget = self.groupList if self.mode == "design" else self.searchCtrl
		wx.CallAfter(focusTarget.SetFocus)

	# ---------------------------------------------------------------
	# وضع التصميم: إضافة عناصر جديدة
	# ---------------------------------------------------------------

	def _addGroup(self):
		dlg = SimpleNameDialog(self, tr("addGroupTitle"), tr("groupNameLabel"))
		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.GetValueEntered()
			if name in self.data:
				ui.message(tr("msgNameExists"))
			else:
				self.data[name] = {}
				saveData(self.data)
				self._populateGroups()
				self._selectAndFocus(self.groupList, name)
				ui.message(tr("msgAdded"))
		dlg.Destroy()

	def _addCategory(self):
		groupIndex = self.groupList.GetSelection()
		if groupIndex == wx.NOT_FOUND:
			ui.message(tr("msgSelectGroupFirst"))
			return
		groupName = self.groupList.GetString(groupIndex)

		dlg = SimpleNameDialog(self, tr("addCategoryTitle"), tr("categoryNameLabel"))
		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.GetValueEntered()
			if name in self.data.get(groupName, {}):
				ui.message(tr("msgNameExistsInGroup"))
			else:
				self.data.setdefault(groupName, {})[name] = {}
				saveData(self.data)
				self._populateCategoriesForGroup(groupName)
				self._selectAndFocus(self.categoryList, name)
				ui.message(tr("msgAdded"))
		dlg.Destroy()

	def _addSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgSelectGroupAndCategoryFirst"))
			return
		groupName = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)

		dlg = SoftwareDialog(self, tr("addSoftwareTitle"))
		if dlg.ShowModal() == wx.ID_OK:
			name, url, url2, notes = dlg.GetValuesEntered()
			if isUrlExists(self.data, url):
				ui.message(tr("msgUrlExists"))
				dlg.Destroy()
				return
			softwareDict = self.data.setdefault(groupName, {}).setdefault(categoryName, {})
			finalName = getUniqueSoftwareName(softwareDict, name)
			softwareDict[finalName] = {"url": url, "url2": url2, "notes": notes}
			removeLocalIgnored(self.data, url)
			saveData(self.data)
			self._populateSoftwareForCategory(groupName, categoryName)
			self._selectAndFocus(self.softwareList, finalName)
			ui.message(tr("msgAdded"))
		dlg.Destroy()

	# ---------------------------------------------------------------
	# وضع التصميم: تعديل عناصر موجودة
	# ---------------------------------------------------------------

	def _editFocusedItem(self):
		focused = self.FindFocus()
		if focused == self.groupList:
			self._editGroup()
		elif focused == self.categoryList:
			self._editCategory()
		elif focused == self.softwareList:
			self._editSoftware()
		else:
			ui.message(tr("msgSelectItemFirst"))

	def _editGroup(self):
		index = self.groupList.GetSelection()
		if index == wx.NOT_FOUND:
			ui.message(tr("msgNoGroupSelected"))
			return
		oldName = self.groupList.GetString(index)

		dlg = SimpleNameDialog(self, tr("editGroupTitle"), tr("groupNameLabel"), initialValue=oldName)
		if dlg.ShowModal() == wx.ID_OK:
			newName = dlg.GetValueEntered()
			if newName != oldName:
				if newName in self.data:
					ui.message(tr("msgNameExists"))
				else:
					reordered = {}
					for key, value in self.data.items():
						reordered[newName if key == oldName else key] = value
					self.data.clear()
					self.data.update(reordered)
					saveData(self.data)
					self._populateGroups()
					self._selectAndFocus(self.groupList, newName)
					ui.message(tr("msgEdited"))
		dlg.Destroy()

	def _editCategory(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoCategorySelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		oldName = self.categoryList.GetString(categoryIndex)

		dlg = SimpleNameDialog(self, tr("editCategoryTitle"), tr("categoryNameLabel"), initialValue=oldName)
		if dlg.ShowModal() == wx.ID_OK:
			newName = dlg.GetValueEntered()
			if newName != oldName:
				categories = self.data.get(groupName, {})
				if newName in categories:
					ui.message(tr("msgNameExistsInGroup"))
				else:
					reordered = {}
					for key, value in categories.items():
						reordered[newName if key == oldName else key] = value
					self.data[groupName] = reordered
					saveData(self.data)
					self._populateCategoriesForGroup(groupName)
					self._selectAndFocus(self.categoryList, newName)
					ui.message(tr("msgEdited"))
		dlg.Destroy()

	def _editSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		softwareIndex = self.softwareList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND or softwareIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)
		oldName = self.softwareList.GetString(softwareIndex)
		info = self.data.get(groupName, {}).get(categoryName, {}).get(oldName, {})

		dlg = SoftwareDialog(
			self, tr("editSoftwareTitle"),
			name=oldName, url=info.get("url", ""), url2=info.get("url2", ""), notes=info.get("notes", "")
		)
		if dlg.ShowModal() == wx.ID_OK:
			newName, url, url2, notes = dlg.GetValuesEntered()
			if isUrlExists(self.data, url, exclude=(groupName, categoryName, oldName)):
				ui.message(tr("msgUrlExists"))
				dlg.Destroy()
				return

			softwareDict = self.data[groupName][categoryName]
			if newName != oldName:
				finalName = getUniqueSoftwareName(softwareDict, newName)
				reordered = {}
				for key, value in softwareDict.items():
					if key == oldName:
						reordered[finalName] = {"url": url, "url2": url2, "notes": notes}
					else:
						reordered[key] = value
				self.data[groupName][categoryName] = reordered
			else:
				finalName = oldName
				softwareDict[oldName] = {"url": url, "url2": url2, "notes": notes}

			removeLocalIgnored(self.data, url)
			saveData(self.data)
			self._populateSoftwareForCategory(groupName, categoryName)
			self._selectAndFocus(self.softwareList, finalName)
			ui.message(tr("msgEdited"))
		dlg.Destroy()

	# ---------------------------------------------------------------
	# وضع التصميم: حذف عناصر
	# ---------------------------------------------------------------

	def _deleteFocusedItem(self):
		focused = self.FindFocus()
		if focused == self.groupList:
			self._deleteGroup()
		elif focused == self.categoryList:
			self._deleteCategory()
		elif focused == self.softwareList:
			self._deleteSoftware()
		else:
			ui.message(tr("msgSelectItemFirst"))

	def _deleteGroup(self):
		index = self.groupList.GetSelection()
		if index == wx.NOT_FOUND:
			ui.message(tr("msgNoGroupSelected"))
			return
		name = self.groupList.GetString(index)
		if confirmYesNo(self, tr("confirmDeleteTitle"), tr("confirmDeleteGroup", name)):
			del self.data[name]
			saveData(self.data)
			self._populateGroups()
			self.groupList.SetFocus()
			ui.message(tr("msgDeleted"))

	def _deleteCategory(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoCategorySelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		name = self.categoryList.GetString(categoryIndex)
		if confirmYesNo(self, tr("confirmDeleteTitle"), tr("confirmDeleteCategory", name)):
			del self.data[groupName][name]
			saveData(self.data)
			self._populateCategoriesForGroup(groupName)
			self.categoryList.SetFocus()
			ui.message(tr("msgDeleted"))

	def _deleteSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		softwareIndex = self.softwareList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND or softwareIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)
		name = self.softwareList.GetString(softwareIndex)
		if confirmYesNo(self, tr("confirmDeleteTitle"), tr("confirmDeleteSoftware", name)):
			info = self.data[groupName][categoryName][name]
			url = info.get("url", "")
			del self.data[groupName][categoryName][name]

			# الحذف المركزي يتطلب: أونلاين + التحقق من المالك + تفعيل Online Design Mode
			isCloudDelete = (
				config.conf["qadreen"]["onlineMode"] and
				getattr(self.plugin, "isRepoOwner", False) and
				getattr(self.plugin, "onlineDesignMode", False)
			)

			if isCloudDelete:
				addCloudDeleted(self.data, url, name, groupName, categoryName)
			else:
				addLocalIgnored(self.data, url, name, groupName, categoryName)

			saveData(self.data)
			self._populateSoftwareForCategory(groupName, categoryName)
			self.softwareList.SetFocus()
			ui.message(tr("msgDeleted"))

	def _selectAndFocus(self, listBox, text):
		index = listBox.FindString(text)
		if index != wx.NOT_FOUND:
			listBox.SetSelection(index)
			listBox.SetFocus()

	# ---------------------------------------------------------------
	# وضع التصميم: نقل/دمج عناصر (مجموعة، فئة، برنامج)
	# ---------------------------------------------------------------

	def _pickFromList(self, title, label, choices):
		dlg = ChoiceDialog(self, title, label, choices)
		result = None
		if dlg.ShowModal() == wx.ID_OK:
			result = dlg.GetSelectedChoice()
		dlg.Destroy()
		return result

	def _askName(self, title, label):
		dlg = SimpleNameDialog(self, title, label)
		result = None
		if dlg.ShowModal() == wx.ID_OK:
			result = dlg.GetValueEntered()
		dlg.Destroy()
		return result

	def _pickOrCreate(self, dialogTitle, label, choices, createNewLabel, createTitle, createLabel):
		result = self._pickFromList(dialogTitle, label, choices)
		if result is None:
			return None
		if result == createNewLabel:
			return self._askName(createTitle, createLabel)
		return result

	# ---------------------------------------------------------------
	# إضافة سريعة من الحافظة (Insert+Shift+C من أي برنامج آخر): نفس
	# نوافذ وضع التصميم المعتادة تماماً، بالرابط معبأً تلقائياً
	# ---------------------------------------------------------------

	def runQuickAdd(self, url, closeWhenDone=True):
		# فحص مبكر: إذا كان رابط الحافظة موجوداً بالفعل، ننبّه ونخرج فوراً
		if url and isUrlExists(self.data, url):
			ui.message(tr("msgUrlExists"))
			if closeWhenDone:
				self.Close()
			return

		createNewLabel = tr("createNewChoice")

		groupChoices = [createNewLabel] + getGroupNames(self.data)
		groupName = self._pickOrCreate(
			tr("quickAddGroupTitle"), tr("groupLabel"), groupChoices,
			createNewLabel, tr("addGroupTitle"), tr("groupNameLabel")
		)
		if groupName is None:
			if closeWhenDone:
				self.Close()
			return

		if groupName not in self.data:
			# مجموعة جديدة كلياً: فئاتها فارغة أصلاً، فنتخطى القائمة
			# مباشرة لمربع كتابة اسم الفئة الجديدة
			categoryName = self._askName(tr("addCategoryTitle"), tr("categoryNameLabel"))
		else:
			categoryChoices = [createNewLabel] + sorted(self.data.get(groupName, {}).keys())
			categoryName = self._pickOrCreate(
				tr("quickAddCategoryTitle"), tr("categoryLabel"), categoryChoices,
				createNewLabel, tr("addCategoryTitle"), tr("categoryNameLabel")
			)
		if categoryName is None:
			if closeWhenDone:
				self.Close()
			return

		dlg = SoftwareDialog(self, tr("addSoftwareTitle"), url=url)
		if dlg.ShowModal() == wx.ID_OK:
			name, finalUrl, url2, notes = dlg.GetValuesEntered()
			if isUrlExists(self.data, finalUrl):
				ui.message(tr("msgUrlExists"))
			else:
				softwareDict = self.data.setdefault(groupName, {}).setdefault(categoryName, {})
				finalName = getUniqueSoftwareName(softwareDict, name)
				softwareDict[finalName] = {"url": finalUrl, "url2": url2, "notes": notes}
				removeLocalIgnored(self.data, finalUrl)
				saveData(self.data)
				ui.message(tr("msgAdded"))
		dlg.Destroy()

		if closeWhenDone:
			self.Close()

	def _moveFocusedItem(self):
		focused = self.FindFocus()
		if focused == self.groupList:
			self._moveGroup()
		elif focused == self.categoryList:
			self._moveCategory()
		elif focused == self.softwareList:
			self._moveSoftware()
		else:
			ui.message(tr("msgSelectItemFirst"))

	def _moveGroup(self):
		index = self.groupList.GetSelection()
		if index == wx.NOT_FOUND:
			ui.message(tr("msgNoGroupSelected"))
			return
		sourceName = self.groupList.GetString(index)

		choices = [name for name in getGroupNames(self.data) if name != sourceName]
		if not choices:
			ui.message(tr("msgNoOtherGroup"))
			return

		targetName = self._pickFromList(tr("moveGroupTitle"), tr("groupLabel"), choices)
		if targetName is None:
			return

		message = tr("confirmMoveGroup", sourceName, targetName)
		if confirmYesNo(self, tr("confirmMoveTitle"), message):
			mergeDict(self.data[targetName], self.data[sourceName])
			del self.data[sourceName]
			saveData(self.data)
			self._populateGroups()
			self._selectAndFocus(self.groupList, targetName)
			ui.message(tr("msgMoved"))

	def _moveCategory(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoCategorySelected"))
			return
		sourceGroup = self.groupList.GetString(groupIndex)
		categoryName = self.categoryList.GetString(categoryIndex)

		choices = [name for name in getGroupNames(self.data) if name != sourceGroup]
		if not choices:
			ui.message(tr("msgNoOtherGroup"))
			return

		targetGroup = self._pickFromList(tr("moveCategoryTitle"), tr("groupLabel"), choices)
		if targetGroup is None:
			return

		message = tr("confirmMoveCategory", categoryName, sourceGroup, targetGroup)
		if confirmYesNo(self, tr("confirmMoveTitle"), message):
			targetCategories = self.data.setdefault(targetGroup, {})
			if categoryName in targetCategories:
				mergeDict(targetCategories[categoryName], self.data[sourceGroup][categoryName])
			else:
				targetCategories[categoryName] = self.data[sourceGroup][categoryName]
			del self.data[sourceGroup][categoryName]
			saveData(self.data)
			self._populateCategoriesForGroup(sourceGroup)
			ui.message(tr("msgMoved"))

	def _moveSoftware(self):
		groupIndex = self.groupList.GetSelection()
		categoryIndex = self.categoryList.GetSelection()
		softwareIndex = self.softwareList.GetSelection()
		if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND or softwareIndex == wx.NOT_FOUND:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		sourceGroup = self.groupList.GetString(groupIndex)
		sourceCategory = self.categoryList.GetString(categoryIndex)
		softwareName = self.softwareList.GetString(softwareIndex)

		groupChoices = getGroupNames(self.data)
		targetGroup = self._pickFromList(tr("moveSoftwareGroupTitle"), tr("groupLabel"), groupChoices)
		if targetGroup is None:
			return

		categoryChoices = sorted(self.data.get(targetGroup, {}).keys())
		if not categoryChoices:
			ui.message(tr("msgNoCategoryInGroup"))
			return

		targetCategory = self._pickFromList(tr("moveSoftwareCategoryTitle"), tr("categoryLabel"), categoryChoices)
		if targetCategory is None:
			return

		if targetGroup == sourceGroup and targetCategory == sourceCategory:
			ui.message(tr("msgSameLocation"))
			return

		message = tr("confirmMoveSoftware", softwareName, targetGroup, targetCategory)
		if confirmYesNo(self, tr("confirmMoveTitle"), message):
			info = self.data[sourceGroup][sourceCategory][softwareName]
			targetCategoryDict = self.data.setdefault(targetGroup, {}).setdefault(targetCategory, {})
			finalName = getUniqueSoftwareName(targetCategoryDict, softwareName)
			targetCategoryDict[finalName] = info
			del self.data[sourceGroup][sourceCategory][softwareName]
			saveData(self.data)
			self._populateSoftwareForCategory(sourceGroup, sourceCategory)
			ui.message(tr("msgMoved"))

	# ---------------------------------------------------------------
	# وضع التصميم: استيراد بيانات من ملف data.json آخر (دمج بدون حذف)
	# ---------------------------------------------------------------

	def _importData(self):
		dlg = wx.FileDialog(
			self,
			message=tr("importDialogTitle"),
			wildcard="data.json|data.json",
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		)
		if dlg.ShowModal() == wx.ID_OK:
			path = dlg.GetPath()
			importedData = None
			try:
				with open(path, "r", encoding="utf-8") as f:
					importedData = json.load(f)
			except (OSError, json.JSONDecodeError):
				importedData = None

			if not isinstance(importedData, dict):
				ui.message(tr("msgImportFailed"))
			else:
				# استبعاد مفتاح البيانات الوصفية من أي ملف مستورد يدوياً، لأنه مفهوم
				# محلي خاص بكل تنصيب على حدة، ولا يجب أن ينتقل أو يُدمج من ملف آخر
				importedData.pop(METADATA_KEY, None)
				addedCount, duplicatedCount = mergeData(self.data, importedData)
				saveData(self.data)
				self._populateGroups()
				ui.message(tr("msgImportSummary", addedCount, duplicatedCount))
		dlg.Destroy()

	# ---------------------------------------------------------------
	# أدوات مساعدة - وضع العرض
	# ---------------------------------------------------------------

	def _getSelectedSoftwareItem(self):
		"""إرجاع (group, category, software, url, url2) للعنصر المحدد في قائمة البرامج"""
		index = self.softwareList.GetSelection()
		if index == wx.NOT_FOUND:
			return None
		clientData = self.softwareList.GetClientData(index)
		if not clientData:
			return None
		groupName, categoryName, softwareName = clientData
		info = self.data.get(groupName, {}).get(categoryName, {}).get(softwareName, {})
		url = info.get("url", "")
		url2 = info.get("url2", "")

		# مزامنة تحديد Group وCategory تلقائياً حتى لو تم الوصول للبرنامج
		# مباشرة عبر البحث
		groupIndex = self.groupList.FindString(groupName)
		if groupIndex != wx.NOT_FOUND:
			self.groupList.SetSelection(groupIndex)

		return groupName, categoryName, softwareName, url, url2

	def _buildCopyBlock(self, name, url, url2):
		"""بناء نص النسخ لبرنامج واحد: الاسم، ثم الرابط الأساسي، ثم الرابط
		الإضافي إن وُجد، كل واحد بسطر مستقل. الملاحظات لا تُنسخ أبداً."""
		lines = [name, url]
		if url2:
			lines.append(url2)
		return "\n".join(lines)

	def _copySelectedAndClose(self):
		item = self._getSelectedSoftwareItem()
		if not item:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName, categoryName, softwareName, url, url2 = item
		if not url:
			ui.message(tr("msgNoLink"))
			return
		api.copyToClip(self._buildCopyBlock(softwareName, url, url2))
		ui.message(tr("msgCopied"))
		self.Close()

	def _openSelectedLink(self):
		item = self._getSelectedSoftwareItem()
		if not item:
			ui.message(tr("msgNoSoftwareSelected"))
			return
		groupName, categoryName, softwareName, url, url2 = item
		if not url:
			ui.message(tr("msgNoLink"))
			return
		webbrowser.open(url)
		ui.message(tr("msgOpeningLink"))

	def _writeClipboard(self):
		blocks = [self._buildCopyBlock(name, url, url2) for name, url, url2 in self.copiedItems]
		api.copyToClip("\n\n".join(blocks))

	def _toggleSharing(self, share):
		if not config.conf["qadreen"]["onlineMode"]:
			ui.message(tr("msgOnlineModeRequired"))
			return

		focused = self.FindFocus()
		if focused == self.groupList:
			index = self.groupList.GetSelection()
			if index == wx.NOT_FOUND:
				ui.message(tr("msgNoGroupSelected"))
				return
			path = [self.groupList.GetString(index)]
		elif focused == self.categoryList:
			groupIndex = self.groupList.GetSelection()
			categoryIndex = self.categoryList.GetSelection()
			if groupIndex == wx.NOT_FOUND or categoryIndex == wx.NOT_FOUND:
				ui.message(tr("msgNoCategorySelected"))
				return
			path = [self.groupList.GetString(groupIndex), self.categoryList.GetString(categoryIndex)]
		else:
			ui.message(tr("msgSelectGroupOrCategoryFirst"))
			return

		if share:
			addSharedPath(self.data, path)
			saveData(self.data)
			ui.message(tr("msgSharingEnabled"))
		else:
			removeSharedPath(self.data, path)
			saveData(self.data)
			ui.message(tr("msgSharingDisabled"))


# =====================================================================
# صفحة إعدادات لغة الإضافة داخل NVDA Settings
# =====================================================================

class QadreenSettingsPanel(gui.settingsDialogs.SettingsPanel):
	# اسم الفئة يبقى "Qadreen" ثابتاً بغض النظر عن اللغة، فهو اسم العلامة
	title = "Qadreen"

	def makeSettings(self, settingsSizer):
		sizerHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		self._languageOptions = ["follow", "ar", "en"]
		choices = [
			tr("settingsFollowNVDA"),
			tr("settingsAlwaysArabic"),
			tr("settingsAlwaysEnglish"),
		]

		self.languageChoice = sizerHelper.addLabeledControl(
			tr("settingsLanguageLabel"),
			wx.Choice,
			choices=choices
		)

		currentValue = config.conf["qadreen"]["language"]
		try:
			currentIndex = self._languageOptions.index(currentValue)
		except ValueError:
			currentIndex = 0
		self.languageChoice.SetSelection(currentIndex)

		# Radio Box for Operation Mode (Offline/Online)
		self.modeChoices = [tr("settingsOfflineMode"), tr("settingsOnlineMode")]
		self.modeRadioBox = sizerHelper.addItem(
			wx.RadioBox(self, label=tr("settingsModeLabel"), choices=self.modeChoices)
		)
		self.modeRadioBox.SetSelection(1 if config.conf["qadreen"]["onlineMode"] else 0)
		self.modeRadioBox.Bind(wx.EVT_RADIOBOX, self.onModeChanged)

		# Cloud Sync Fields (Gist ID and PAT)
		self.gistIdCtrl = sizerHelper.addLabeledControl(tr("settingsGistIdLabel"), wx.TextCtrl)
		self.gistIdCtrl.SetValue(config.conf["qadreen"]["gistId"])

		self.patCtrl = sizerHelper.addLabeledControl(
			tr("settingsPatLabel"), wx.TextCtrl, style=wx.TE_PASSWORD
		)
		self.patCtrl.SetValue(crypto_manager.decrypt_token(config.conf["qadreen"]["pat"]))

		# Security Warning Label
		warningLabel = wx.StaticText(self, label=tr("settingsPatWarning"))
		sizerHelper.addItem(warningLabel)

		# Sync source: Gist or repository.
		self.sourceTypeChoices = [tr("settingsSourceGist"), tr("settingsSourceRepo")]
		self.sourceTypeRadioBox = sizerHelper.addItem(
			wx.RadioBox(self, label=tr("settingsSourceTypeLabel"), choices=self.sourceTypeChoices)
		)
		self.sourceTypeRadioBox.SetSelection(
			1 if config.conf["qadreen"]["sourceType"] == "repo" else 0
		)
		self.sourceTypeRadioBox.Bind(wx.EVT_RADIOBOX, self.onSourceTypeChanged)

		self.repoOwnerNameCtrl = sizerHelper.addLabeledControl(
			tr("settingsRepoOwnerNameLabel"), wx.TextCtrl
		)
		self.repoOwnerNameCtrl.SetValue(config.conf["qadreen"]["repoOwnerName"])

		self.repoPathCtrl = sizerHelper.addLabeledControl(
			tr("settingsRepoPathLabel"), wx.TextCtrl
		)
		self.repoPathCtrl.SetValue(config.conf["qadreen"]["repoPath"])

		self.repoBranchCtrl = sizerHelper.addLabeledControl(
			tr("settingsRepoBranchLabel"), wx.TextCtrl
		)
		self.repoBranchCtrl.SetValue(config.conf["qadreen"]["repoBranch"])

		self.repoPatCtrl = sizerHelper.addLabeledControl(
			tr("settingsRepoPatLabel"), wx.TextCtrl, style=wx.TE_PASSWORD
		)
		self.repoPatCtrl.SetValue(crypto_manager.decrypt_token(config.conf["qadreen"]["repoPat"]))

		repoWarningLabel = wx.StaticText(self, label=tr("settingsRepoPatWarning"))
		sizerHelper.addItem(repoWarningLabel)

		# Initialize the enabled/disabled state based on current selection
		self._updateOnlineFieldsState()

		self.contactButton = sizerHelper.addItem(
			wx.Button(self, label=tr("contactDeveloperButton"))
		)
		self.contactButton.Bind(wx.EVT_BUTTON, self.onContactDeveloper)

	def onModeChanged(self, event):
		self._updateOnlineFieldsState()

	def onSourceTypeChanged(self, event):
		self._updateOnlineFieldsState()

	def _updateOnlineFieldsState(self):
		isOnline = self.modeRadioBox.GetSelection() == 1
		isRepo = self.sourceTypeRadioBox.GetSelection() == 1

		self.sourceTypeRadioBox.Enable(isOnline)
		self.gistIdCtrl.Enable(isOnline and not isRepo)
		self.patCtrl.Enable(isOnline and not isRepo)
		self.repoOwnerNameCtrl.Enable(isOnline and isRepo)
		self.repoPathCtrl.Enable(isOnline and isRepo)
		self.repoBranchCtrl.Enable(isOnline and isRepo)
		self.repoPatCtrl.Enable(isOnline and isRepo)

	def onContactDeveloper(self, event):
		email = "saedmohamed.n2210@gmail.com"
		subject = urllib.parse.quote("Qadreen")
		webbrowser.open("mailto:{}?subject={}".format(email, subject))

	def onSave(self):
		selectedIndex = self.languageChoice.GetSelection()
		if selectedIndex != wx.NOT_FOUND:
			config.conf["qadreen"]["language"] = self._languageOptions[selectedIndex]

		config.conf["qadreen"]["onlineMode"] = (self.modeRadioBox.GetSelection() == 1)
		config.conf["qadreen"]["gistId"] = self.gistIdCtrl.GetValue().strip()
		config.conf["qadreen"]["pat"] = crypto_manager.encrypt_token(self.patCtrl.GetValue().strip())
		config.conf["qadreen"]["sourceType"] = (
			"repo" if self.sourceTypeRadioBox.GetSelection() == 1 else "gist"
		)
		config.conf["qadreen"]["repoOwnerName"] = self.repoOwnerNameCtrl.GetValue().strip()
		config.conf["qadreen"]["repoPath"] = self.repoPathCtrl.GetValue().strip()
		config.conf["qadreen"]["repoBranch"] = self.repoBranchCtrl.GetValue().strip()
		config.conf["qadreen"]["repoPat"] = crypto_manager.encrypt_token(self.repoPatCtrl.GetValue().strip())


# =====================================================================
# محرك المزامنة السحابية التعاونية (GitHub Gist)
# =====================================================================

GIST_FILENAME = "qadreen_data.json"
GIST_API_URL_TEMPLATE = "https://api.github.com/gists/{}"
CONTENTS_API_URL_TEMPLATE = "https://api.github.com/repos/{}/contents/{}"
GITHUB_USER_API = "https://api.github.com/user"
SYNC_INTERVAL_SECONDS = 6 * 60 * 60  # 21600 seconds (6 hours)
syncLock = threading.Lock()


def fetchCloudData(gistId, pat):
	request = urllib.request.Request(
		GIST_API_URL_TEMPLATE.format(gistId),
		headers={
			"Authorization": "token {}".format(pat),
			"Accept": "application/vnd.github+json",
			"User-Agent": "Qadreen-NVDA-Addon",
		}
	)
	with urllib.request.urlopen(request, timeout=20) as response:
		gistData = json.loads(response.read().decode("utf-8"))

	fileInfo = gistData.get("files", {}).get(GIST_FILENAME)
	if fileInfo is None:
		return {}
	content = fileInfo.get("content", "").strip()
	return json.loads(content) if content else {}


def pushCloudData(gistId, pat, payload):
	body = json.dumps({
		"files": {
			GIST_FILENAME: {
				"content": json.dumps(payload, ensure_ascii=False, indent="\t")
			}
		}
	}).encode("utf-8")

	request = urllib.request.Request(
		GIST_API_URL_TEMPLATE.format(gistId),
		data=body,
		method="PATCH",
		headers={
			"Authorization": "token {}".format(pat),
			"Accept": "application/vnd.github+json",
			"Content-Type": "application/json",
			"User-Agent": "Qadreen-NVDA-Addon",
		}
	)
	with urllib.request.urlopen(request, timeout=20) as response:
		response.read()  # Execute request, response content is not needed


def _buildEncodedRepoPath(rawPath):
	"""Clean and encode each repository-path component separately."""
	cleanPath = rawPath.strip().strip("/") or GIST_FILENAME
	return "/".join(urllib.parse.quote(part) for part in cleanPath.split("/"))


def fetchRepoData(ownerName, path, branch, pat):
	"""Return repository data and its current SHA; a missing file is empty data."""
	encodedPath = _buildEncodedRepoPath(path)
	url = "{}?ref={}".format(
		CONTENTS_API_URL_TEMPLATE.format(ownerName, encodedPath),
		urllib.parse.quote(branch)
	)
	request = urllib.request.Request(
		url,
		headers={
			"Authorization": "token {}".format(pat),
			"Accept": "application/vnd.github+json",
			"User-Agent": "Qadreen-NVDA-Addon",
		}
	)
	try:
		with urllib.request.urlopen(request, timeout=20) as response:
			fileInfo = json.loads(response.read().decode("utf-8"))
	except urllib.error.HTTPError as e:
		if e.code == 404:
			return {}, None
		raise

	content = base64.b64decode(fileInfo["content"]).decode("utf-8").strip()
	data = json.loads(content) if content else {}
	return data, fileInfo["sha"]


def pushRepoData(ownerName, path, branch, pat, payload, previousSha):
	"""Upload data to a repository file using the SHA obtained during fetch."""
	encodedPath = _buildEncodedRepoPath(path)
	url = CONTENTS_API_URL_TEMPLATE.format(ownerName, encodedPath)
	body = {
		"message": "Qadreen data sync",
		"content": base64.b64encode(
			json.dumps(payload, ensure_ascii=False, indent="\t").encode("utf-8")
		).decode("ascii"),
		"branch": branch,
	}
	if previousSha is not None:
		body["sha"] = previousSha

	request = urllib.request.Request(
		url,
		data=json.dumps(body).encode("utf-8"),
		method="PUT",
		headers={
			"Authorization": "token {}".format(pat),
			"Accept": "application/vnd.github+json",
			"Content-Type": "application/json",
			"User-Agent": "Qadreen-NVDA-Addon",
		}
	)
	with urllib.request.urlopen(request, timeout=20) as response:
		response.read()


def authenticateRepoUser(repoOwnerName, repoPat):
	"""
	التحقق من هوية مستخدم GitHub عبر طلب GET إلى https://api.github.com/user
	واستخراج اسم المالك الفعلي من صيغة (owner/repository) ومقارنته بقيمة login.
	
	تعيد (True, "owner") إذا تطابق المستخدم مع المالك.
	تعيد (False, "collaborator") إذا نجح التحقق ولكن المستخدم مختلف عن المالك.
	تعيد (False, "error") في حال فشل الاتصال أو عدم صحة التوكن أو خطأ في البيانات.
	"""
	cleanOwner = repoOwnerName.strip().lower()
	cleanPat = repoPat.strip()
	if not cleanOwner or not cleanPat:
		return False, "error"

	actualOwner = cleanOwner.split("/", 1)[0].strip()
	if not actualOwner:
		return False, "error"

	request = urllib.request.Request(
		GITHUB_USER_API,
		headers={
			"Authorization": "token {}".format(cleanPat),
			"Accept": "application/vnd.github+json",
			"User-Agent": "Qadreen-NVDA-Addon",
		}
	)
	try:
		with urllib.request.urlopen(request, timeout=15) as response:
			userData = json.loads(response.read().decode("utf-8"))
		login = userData.get("login", "")
		if login and login.strip().lower() == actualOwner:
			return True, "owner"
		return False, "collaborator"
	except Exception as e:
		log.error("Qadreen: GitHub user authentication failed: {}".format(e))
		return False, "error"


def getDatasetUrls(data):
	"""جمع كافة الروابط الموجودة في هيكل البيانات (مع تجاهل المفتاح الوصفي __metadata__)."""
	urls = set()
	for groupName, categories in data.items():
		if groupName == METADATA_KEY or not isinstance(categories, dict):
			continue
		for categoryName, softwareDict in categories.items():
			if not isinstance(softwareDict, dict):
				continue
			for softwareName, info in softwareDict.items():
				if isinstance(info, dict):
					url = info.get("url", "").strip()
					if url:
						urls.add(url)
	return urls


def removeSoftwareByUrls(data, urlsToRemove):
	"""
	حذف أي برنامج يحمل أحد الروابط المحددة من البيانات المحلية.
	يتم التنظيف التلقائي للفئات والمجموعات الفارغة فقط إذا تم إفراغها بواسطة هذه الدالة،
	مع الحفاظ المطلق على القوالب الفارغة مسبقاً.
	"""
	if not urlsToRemove:
		return False

	urlsSet = set(u.strip() for u in urlsToRemove if u.strip())
	changed = False

	for groupName, categories in list(data.items()):
		if groupName == METADATA_KEY or not isinstance(categories, dict):
			continue

		group_changed = False
		for categoryName, softwareDict in list(categories.items()):
			if not isinstance(softwareDict, dict):
				continue

			category_changed = False
			for softwareName, info in list(softwareDict.items()):
				if isinstance(info, dict) and info.get("url", "").strip() in urlsSet:
					del softwareDict[softwareName]
					category_changed = True
					group_changed = True
					changed = True

			# الحذف الآمن: نحذف الفئة فقط إذا كانت فارغة *وبسبب* تدخلنا المباشر في هذه الدورة
			if category_changed and not softwareDict:
				del categories[categoryName]

		# الحذف الآمن للمجموعة: فقط إذا فرغت *وبسبب* تدخلنا المباشر
		if group_changed and not categories:
			del data[groupName]

	return changed


def mergeCloudToLocal(localData, cloudData):
	"""
	دمج البيانات السحابية داخل البيانات المحلية مع مراعاة:
	1. المانع الوحيد لدخول السحابة هو cloud_deleted_urls.
	2. سيادة السحابة: التعديل المركزي ينسخ أو يمسح التعديل/الحذف المحلي.
	"""
	cloudTombstones = set(item.get("url", "").strip() for item in getCloudDeleted(cloudData))

	addedCount = 0
	for groupName, categories in cloudData.items():
		if groupName == METADATA_KEY or not isinstance(categories, dict):
			continue
		for categoryName, softwareDict in categories.items():
			if not isinstance(softwareDict, dict):
				continue
			for softwareName, info in softwareDict.items():
				if not isinstance(info, dict):
					continue
				url = info.get("url", "").strip()
				if not url or url in cloudTombstones:
					continue

				removeSoftwareByUrls(localData, [url])
				removeLocalIgnored(localData, url)

				targetGroup = localData.setdefault(groupName, {})
				targetCategory = targetGroup.setdefault(categoryName, {})
				finalName = getUniqueSoftwareName(targetCategory, softwareName)
				targetCategory[finalName] = copy.deepcopy(info)
				addedCount += 1

	return addedCount


def _buildSharedLocalData(localData):
	"""تجميع المجموعات والفئات المشتركة محلياً فقط لرفعها، مع استبعاد أي روابط محظورة محلياً."""
	sharedLocalData = {}
	localIgnoredUrls = set(item.get("url", "").strip() for item in getLocalIgnored(localData))

	for path in getSharedItems(localData):
		if len(path) == 1:
			groupName = path[0]
			if groupName in localData and isinstance(localData[groupName], dict):
				for catName, sDict in localData[groupName].items():
					if not isinstance(sDict, dict):
						continue
					filteredDict = {
						sName: copy.deepcopy(sInfo)
						for sName, sInfo in sDict.items()
						if isinstance(sInfo, dict) and sInfo.get("url", "").strip() and sInfo.get("url", "").strip() not in localIgnoredUrls
					}
					if filteredDict:
						sharedLocalData.setdefault(groupName, {})[catName] = filteredDict
		elif len(path) == 2:
			groupName, categoryName = path
			if groupName in localData and categoryName in localData.get(groupName, {}):
				sDict = localData[groupName][categoryName]
				if isinstance(sDict, dict):
					filteredDict = {
						sName: copy.deepcopy(sInfo)
						for sName, sInfo in sDict.items()
						if isinstance(sInfo, dict) and sInfo.get("url", "").strip() and sInfo.get("url", "").strip() not in localIgnoredUrls
					}
					if filteredDict:
						sharedLocalData.setdefault(groupName, {})[categoryName] = filteredDict
	return sharedLocalData


def buildSyncPayload(cloudData, localData, isCentralAuthority):
	"""
	بناء حمولة البيانات الجاهزة للرفع إلى السحابة بحسب نوع الصلاحية:
	- Central Authority (Owner في Online Design Mode):
	  يحق له رفع التعديلات على البرامج المشتركة الحالية، وتحديث قائمة المحذوفات المركزية cloud_deleted_urls، وتطهير السحابة من البرامج المحذوفة.
	- Collaborator (المتعاون):
	  يرفع فقط البرامج الجديدة التي لا يوجد لها رابط في السحابة ولا في المحذوفات المركزية، ولا يمس المحذوفات السحابية إطلاقاً.
	- كلا الوضعين: لا تُرفع local_ignored_urls إلى السحابة أبداً.
	"""
	payload = copy.deepcopy(cloudData)
	sharedLocalData = _buildSharedLocalData(localData)

	if isCentralAuthority:
		# دمج المحذوفات المركزية المحلية في السحابة
		localCloudDeleted = getCloudDeleted(localData)
		for item in localCloudDeleted:
			url = item.get("url", "").strip()
			if url:
				addCloudDeleted(payload, url, item.get("name", ""), item.get("group", ""), item.get("category", ""))

		# تطبيق المحذوفات المركزية على حمولة الرفع وتطهيرها من أي برامج محذوفة
		cloudTombstones = set(item.get("url", "").strip() for item in getCloudDeleted(payload))
		removeSoftwareByUrls(payload, cloudTombstones)

		# رفع كافة البرامج المشتركة المحلية (إضافة جديدة أو تحديث تعديلات مركزية)
		for groupName, categories in sharedLocalData.items():
			for categoryName, softwareDict in categories.items():
				for softwareName, info in softwareDict.items():
					url = info.get("url", "").strip()
					if not url or url in cloudTombstones:
						continue
					removeSoftwareByUrls(payload, [url])
					targetGroup = payload.setdefault(groupName, {})
					targetCategory = targetGroup.setdefault(categoryName, {})
					finalName = getUniqueSoftwareName(targetCategory, softwareName)
					targetCategory[finalName] = copy.deepcopy(info)
	else:
		# وضع المتعاون: لا يمس المحذوفات السحابية ولا يعدل برامج السحابة الحالية
		existingCloudUrls = getDatasetUrls(cloudData)
		cloudTombstones = set(item.get("url", "").strip() for item in getCloudDeleted(cloudData))

		for groupName, categories in sharedLocalData.items():
			for categoryName, softwareDict in categories.items():
				for softwareName, info in softwareDict.items():
					url = info.get("url", "").strip()
					if not url or url in existingCloudUrls or url in cloudTombstones:
						continue
					targetGroup = payload.setdefault(groupName, {})
					targetCategory = targetGroup.setdefault(categoryName, {})
					finalName = getUniqueSoftwareName(targetCategory, softwareName)
					targetCategory[finalName] = copy.deepcopy(info)

	# حماية الخصوصية ومنع تسريب local_ignored_urls نهائياً إلى السحابة
	if METADATA_KEY in payload:
		payload[METADATA_KEY].pop("local_ignored_urls", None)
		if not payload[METADATA_KEY]:
			payload.pop(METADATA_KEY, None)

	return payload


def fetchRemoteData(sourceType, conf):
	"""جلب البيانات السحابية الحالية وقيمة SHA إن وجدت."""
	if sourceType == "repo":
		ownerName = conf["repoOwnerName"].strip()
		path = conf["repoPath"].strip() or GIST_FILENAME
		branch = conf["repoBranch"].strip() or "main"
		pat = crypto_manager.decrypt_token(conf["repoPat"].strip())
		if not ownerName or not pat:
			return None, None
		return fetchRepoData(ownerName, path, branch, pat)
	else:
		gistId = conf["gistId"].strip()
		pat = crypto_manager.decrypt_token(conf["pat"].strip())
		if not gistId or not pat:
			return None, None
		cloudData = fetchCloudData(gistId, pat)
		return cloudData, None


def pushRemoteData(sourceType, conf, payload, previousSha=None):
	"""رفع حمولة البيانات إلى السحابة."""
	if sourceType == "repo":
		ownerName = conf["repoOwnerName"].strip()
		path = conf["repoPath"].strip() or GIST_FILENAME
		branch = conf["repoBranch"].strip() or "main"
		pat = crypto_manager.decrypt_token(conf["repoPat"].strip())
		pushRepoData(ownerName, path, branch, pat, payload, previousSha)
	else:
		gistId = conf["gistId"].strip()
		pat = crypto_manager.decrypt_token(conf["pat"].strip())
		pushCloudData(gistId, pat, payload)


def performSync(pluginInstance=None):
	"""
	تنفيذ دورة المزامنة السحابية وفق سياسة سيادة السحابة وصلاحيات المستخدم:
	1. منع التزامن المتعدد بواسطة syncLock غير معطل للواجهة.
	2. استيراد المحذوفات السحابية وتطهير البيانات المحلية منها.
	3. دمج البيانات السحابية مع تفوق السحابة في التحديث المركزي.
	4. بناء حمولة الرفع حسب صلاحية المستخدم (Central Authority أو Collaborator).
	5. معالجة تعارضات المستودع (409/422) بإعادة المحاولة لمرة واحدة بـ SHA حديث.
	"""
	if not config.conf["qadreen"]["onlineMode"]:
		return

	if not syncLock.acquire(blocking=False):
		log.info("Qadreen: Sync is already in progress, skipping overlapping execution.")
		return

	try:
		sourceType = config.conf["qadreen"]["sourceType"]
		qadreenConf = config.conf["qadreen"]

		isCentralAuthority = bool(
			pluginInstance
			and getattr(pluginInstance, "isRepoOwner", False)
			and getattr(pluginInstance, "onlineDesignMode", False)
		)

		cloudData, sha = fetchRemoteData(sourceType, qadreenConf)
		if cloudData is None:
			return

		localData = loadData()

		# استيراد المحذوفات السحابية المركزية إلى السجلات المحلية وتطهير localData منها
		remoteTombstones = getCloudDeleted(cloudData)
		for item in remoteTombstones:
			url = item.get("url", "").strip()
			if url:
				addCloudDeleted(localData, url, item.get("name", ""), item.get("group", ""), item.get("category", ""))

		allTombstones = set(item.get("url", "").strip() for item in getCloudDeleted(localData))
		removeSoftwareByUrls(localData, allTombstones)

		# دمج البيانات السحابية وفق قاعدة Cloud is the Boss
		mergeCloudToLocal(localData, cloudData)
		saveData(localData)
		if pluginInstance is not None:
			pluginInstance.data = localData

		payload = buildSyncPayload(cloudData, localData, isCentralAuthority)

		try:
			pushRemoteData(sourceType, qadreenConf, payload, sha)
		except urllib.error.HTTPError as e:
			if sourceType == "repo" and e.code in (409, 422):
				log.info("Qadreen: Remote conflict (%s), retrying sync once with fresh SHA", e.code)
				cloudData, sha = fetchRemoteData(sourceType, qadreenConf)
				if cloudData is not None:
					remoteTombstones = getCloudDeleted(cloudData)
					for item in remoteTombstones:
						url = item.get("url", "").strip()
						if url:
							addCloudDeleted(localData, url, item.get("name", ""), item.get("group", ""), item.get("category", ""))
					allTombstones = set(item.get("url", "").strip() for item in getCloudDeleted(localData))
					removeSoftwareByUrls(localData, allTombstones)
					mergeCloudToLocal(localData, cloudData)
					saveData(localData)
					if pluginInstance is not None:
						pluginInstance.data = localData
					payload = buildSyncPayload(cloudData, localData, isCentralAuthority)
					pushRemoteData(sourceType, qadreenConf, payload, sha)
			else:
				raise
	except Exception as e:
		log.error("Qadreen: performSync encountered an error: %s", e, exc_info=True)
	finally:
		syncLock.release()


def runSyncCycle(pluginInstance):
	performSync(pluginInstance)
	scheduleSyncTimer(pluginInstance)


def scheduleSyncTimer(pluginInstance):
	if not config.conf["qadreen"]["onlineMode"]:
		return
	if getattr(pluginInstance, "_syncTimer", None) is not None:
		try:
			pluginInstance._syncTimer.cancel()
		except Exception:
			pass
		pluginInstance._syncTimer = None
	timer = threading.Timer(SYNC_INTERVAL_SECONDS, runSyncCycle, args=(pluginInstance,))
	timer.daemon = True
	pluginInstance._syncTimer = timer
	timer.start()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "Qadreen"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.data = loadData()
		self._dialog = None
		self._helpDialog = None
		self._deletedItemsDialog = None
		self.isRepoOwner = False
		self.onlineDesignMode = False
		self._authInProgress = False
		self._isTerminated = False
		if QadreenSettingsPanel not in gui.NVDASettingsDialog.categoryClasses:
			gui.NVDASettingsDialog.categoryClasses.append(QadreenSettingsPanel)
		threading.Thread(target=checkForUpdateInBackground, daemon=True).start()
		self._syncTimer = None
		if config.conf["qadreen"]["onlineMode"]:
			# مزامنة فورية عند الإقلاع في خيط منفصل
			threading.Thread(target=performSync, args=(self,), daemon=True).start()
			scheduleSyncTimer(self)

	@script(
		# يُحدد وصف الاختصار عند تحميل الإضافة وفقًا للغة Qadreen الحالية.
		# يتطلب تغيير الوصف في Input Gestures إعادة تشغيل NVDA.
		description=tr("scriptDescription"),
		gesture="kb:NVDA+control+q"
	)
	def script_openQuickSearch(self, gesture):
		if self._dialog is not None:
			try:
				self._dialog.Raise()
				return
			except RuntimeError:
				self._dialog = None

		# إعادة تحميل البيانات من الملف في كل مرة تفتح فيها النافذة
		self.data = loadData()

		parentWindow = wx.GetApp().TopWindow if wx.GetApp() else None
		self._dialog = SearchDialog(parentWindow, self.data, plugin=self)
		self._dialog.Bind(wx.EVT_CLOSE, self._onDialogClose)
		self._dialog.Show()
		wx.CallAfter(self._dialog.searchCtrl.SetFocus)

	def _onDialogClose(self, event):
		if self._dialog is not None:
			self._dialog.Destroy()
			self._dialog = None

	@script(
		description=tr("helpScriptDescription"),
		gesture="kb:NVDA+control+h"
	)
	def script_openHelp(self, gesture):
		if getattr(self, "_helpDialog", None) is not None:
			try:
				self._helpDialog.Raise()
				return
			except RuntimeError:
				self._helpDialog = None

		self._helpDialog = HelpDialog(gui.mainFrame)
		self._helpDialog.Bind(wx.EVT_CLOSE, self._onHelpDialogClose)
		self._helpDialog.Show()

	def _onHelpDialogClose(self, evt):
		if self._helpDialog:
			self._helpDialog.Destroy()
			self._helpDialog = None

	@script(
		description=tr("quickAddScriptDescription"),
		gesture="kb:NVDA+shift+c"
	)
	def script_quickAddFromClipboard(self, gesture):
		try:
			clipboardText = api.getClipData().strip()
		except Exception:
			clipboardText = ""
		if not clipboardText:
			ui.message(tr("msgClipboardEmpty"))
			return

		wasAlreadyOpen = self._dialog is not None
		if self._dialog is None:
			self.data = loadData()
			parentWindow = wx.GetApp().TopWindow if wx.GetApp() else None
			self._dialog = SearchDialog(parentWindow, self.data, startMode="design", plugin=self)
			self._dialog.Bind(wx.EVT_CLOSE, self._onDialogClose)
			self._dialog.Show()
		elif self._dialog.mode != "design":
			self._dialog._toggleMode()

		wx.CallAfter(self._dialog.runQuickAdd, clipboardText, not wasAlreadyOpen)

	@script(
		description=tr("deletedItemsScriptDescription"),
		gesture="kb:control+-"
	)
	def script_openDeletedItems(self, gesture):
		if self._deletedItemsDialog is not None:
			try:
				self._deletedItemsDialog.Raise()
				return
			except RuntimeError:
				self._deletedItemsDialog = None

		self.data = loadData()
		parentWindow = wx.GetApp().TopWindow if wx.GetApp() else None
		self._deletedItemsDialog = DeletedItemsDialog(parentWindow, self.data, self)
		self._deletedItemsDialog.Bind(wx.EVT_CLOSE, self._onDeletedItemsDialogClose)
		self._deletedItemsDialog.Show()

	def _onDeletedItemsDialogClose(self, event):
		if self._deletedItemsDialog is not None:
			self._deletedItemsDialog.Destroy()
			self._deletedItemsDialog = None

	@script(
		description=tr("onlineDesignModeScriptDescription"),
		gesture="kb:control+shift+d"
	)
	def script_toggleOnlineDesignMode(self, gesture):
		if not config.conf["qadreen"]["onlineMode"]:
			ui.message(tr("msgOnlineDesignOffline"))
			return

		if self.onlineDesignMode:
			self.onlineDesignMode = False
			ui.message(tr("msgOnlineDesignModeDisabled"))
			return

		if self._authInProgress:
			ui.message(tr("msgAuthInProgress"))
			return

		repoOwnerName = config.conf["qadreen"]["repoOwnerName"].strip()
		repoPat = crypto_manager.decrypt_token(config.conf["qadreen"]["repoPat"].strip())
		if not repoOwnerName or not repoPat:
			ui.message(tr("msgGitHubCredentialsMissing"))
			return

		ui.message(tr("msgVerifyingUser"))
		self._authInProgress = True

		def worker():
			isOwner, reason = authenticateRepoUser(repoOwnerName, repoPat)
			wx.CallAfter(self._onAuthFinished, isOwner, reason)

		threading.Thread(target=worker, daemon=True).start()

	def _onAuthFinished(self, isOwner, reason):
		if getattr(self, "_isTerminated", False):
			return
		self._authInProgress = False
		if isOwner:
			self.isRepoOwner = True
			self.onlineDesignMode = True
			ui.message(tr("msgOnlineDesignModeEnabled"))
			if config.conf["qadreen"]["onlineMode"]:
				threading.Thread(target=performSync, args=(self,), daemon=True).start()
		elif reason == "collaborator":
			self.isRepoOwner = False
			self.onlineDesignMode = False
			ui.message(tr("msgOwnerOnly"))
		else:
			self.isRepoOwner = False
			self.onlineDesignMode = False
			ui.message(tr("msgAuthFailed"))

	def terminate(self, *args, **kwargs):
		self._isTerminated = True
		if getattr(self, "_deletedItemsDialog", None) is not None:
			self._deletedItemsDialog.Destroy()
			self._deletedItemsDialog = None
		if getattr(self, "_syncTimer", None) is not None:
			self._syncTimer.cancel()
		super().terminate(*args, **kwargs)
		if QadreenSettingsPanel in gui.NVDASettingsDialog.categoryClasses:
			gui.NVDASettingsDialog.categoryClasses.remove(QadreenSettingsPanel)
