// an Error that the generic handler in index.js renders with this HTTP status
const httpError = (status, message) => {
    const err = new Error(message);
    err.status = status;
    return err;
};

module.exports = {
    httpError
};