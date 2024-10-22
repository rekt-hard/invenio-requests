// This file is part of React-Invenio-Deposit
// Copyright (C) 2021-2024 Graz University of Technology.
//
// Invenio-app-rdm is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

const { appendFileSync, readdirSync, readFileSync, writeFileSync } = require("fs");
const { gettextToI18next } = require("i18next-conv");

const PACKAGE_MESSAGES_PATH = "./messages";

// it accepts the same options as the cli.
// https://github.com/i18next/i18next-gettext-converter#options
const options = {
  /* you options here */
};

function save(target) {
  return (result) => {
    writeFileSync(target, result);
  };
}

function compileAndCreateFileForLanguage(parentPath, lang) {
  gettextToI18next(
    lang,
    readFileSync(`${parentPath}/${lang}/messages.po`),
    options
  ).then(save(`${parentPath}/${lang}/translations.json`));
}

function writeGeneratedTranslationsFile(languages) {
  const generatedTranslationsFilePath = `${PACKAGE_MESSAGES_PATH}/_generatedTranslations.js`;
  writeFileSync(
    generatedTranslationsFilePath,
    "// This is an auto generated file to import and export all available translations.\n" +
      "// Changes should not be checked into version control.\n"
  );

  for (const lang of languages) {
    appendFileSync(
      generatedTranslationsFilePath,
      `import TRANSLATE_${lang.toUpperCase()} from "./${lang}/translations.json";\n`
    );
  }

  appendFileSync(generatedTranslationsFilePath, `\nexport const translations = {\n`);
  for (const lang of languages) {
    appendFileSync(
      generatedTranslationsFilePath,
      `  ${lang}: { translation: TRANSLATE_${lang} },\n`
    );
  }
  appendFileSync(generatedTranslationsFilePath, `};\n`);
}

if ("lang" === process.argv[2]) {
  const lang = process.argv[3];
  compileAndCreateFileForLanguage(`${PACKAGE_MESSAGES_PATH}`, lang);
} else {
  // Since we use Transifex for managing translations, the pulled .po files have to
  // be converted to .json files in order to be used by the application.
  const directories = readdirSync(`${PACKAGE_MESSAGES_PATH}`, {
    withFileTypes: true,
  }).filter((dir) => dir.isDirectory());

  // We now assume we are dealing with directories containing a messages.po file
  // - read input file containing translations (e.g. de.po)
  // - write compiled output file containing translations to be used by the application (e.g. de.json)
  let languages = [];
  for (const directory of directories) {
    compileAndCreateFileForLanguage(directory.parentPath, directory.name);
    languages.push(directory.name);
  }

  // - write file containing translations for static import in i18next.js
  writeGeneratedTranslationsFile(languages);
}
