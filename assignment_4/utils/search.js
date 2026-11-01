// ILIKE pattern matching `text` anywhere, with % _ \ in the text taken literally
// (backslash is PostgreSQL's default LIKE escape character)
const containsPattern = (text) => `%${text.replace(/[\\%_]/g, '\\$&')}%`;

module.exports = {
    containsPattern
};
