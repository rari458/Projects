const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();
const { nanoid } = require('nanoid');
const Url = require('./models/Url');

const app = express();
const PORT = process.env.PORT || 5000;
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

app.use(cors());
app.use(express.json());

mongoose.connect(process.env.MONGO_URI)
	.then(() => console.log('MongoDB connected successfully!'))
	.catch((err) => console.error('MongoDB connection error:', err));

app.get('/', (req, res) => {
	res.send('Hello from URL Shortener Backend!');
});

app.post('/api/shorten', async (req, res) => {
	const { originalUrl, customCode, expiration } = req.body;

	if (!originalUrl) {
		return res.status(400).json({ error: 'Original URL is required' });
	}

	try {
		let shortCode;

		if (customCode) {
			const existing = await Url.findOne({ shortCode: customCode });

			if (existing) {
				return res.status(409).json({
					error: '이 사용자 정의 이름은 이미 사용 중입니다.'
				});
			}
			shortCode = customCode;
		} else {
			let url = await Url.findOne({ originalUrl });
			if (url) {
				return res.json({
					message: 'Short URL already exists.',
					shortUrl: `${BASE_URL}/${url.shortCode}`,
					clicks: url.clicks
				});
			}
			shortCode = nanoid(7);
		}

		let expireAt = null;

		if (expiration && expiration !== 'never') {
			const now = new Date();
			if (expiration === '1day') {
				now.setDate(now.getDate() + 1);
			} else if (expiration === '7days') {
				now.setDate(now.getDate() + 7);
			} else if (expiration === '1hour') {
				now.setHours(now.getHours() + 1);
			}
			expireAt = now;
		}

		const url = new Url({
			originalUrl,
			shortCode,
			expireAt: expireAt
		});

		await url.save();

		res.status(201).json({
			message: 'Short URL created successfully.',
			shortUrl: `${BASE_URL}/${url.shortCode}`,
			clicks: url.clicks
		});
		
	} catch (err) {
		console.error('Error creating short URL:', err);
		res.status(500).json({ error: 'Server error' });
	}
});

app.get('/:shortCode', async (req, res) => {
	const { shortCode } = req.params;

	try {
		const url = await Url.findOne({ shortCode });

		if (url) {
			url.clicks++;
			await url.save();
			return res.redirect(301, url.originalUrl);
		} else {
			return res.status(404).json({ error: 'URL not found' });
		}
	} catch (err) {
		console.error('Redirect error:', err);
		res.status(500).json({ error: 'Server error' });
	}
});

app.listen(PORT, () => {
	console.log(`Server is running on port ${PORT}`);
});
