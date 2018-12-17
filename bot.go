package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/gocolly/colly"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/go-telegram-bot-api/telegram-bot-api"
)

type post struct {
	URL       string
	Timestamp int64
	Author    string
	Comment   string
	Images    []string
}

var (
	TOKEN = os.Getenv("token")
	URL   = "https://www.kaffee-netz.de"
)

var topics = map[string]string{
	"Wie sieht eure Kaffee-Ecke aus?":                     "/threads/wie-sieht-eure-kaffee-ecke-aus.13966",
	"Der \"Ich habe gerade Kaffeekram gekauft\" Thread":   "/threads/der-ich-habe-gerade-kaffeekram-gekauft-thread.62180",
	"Und plötzlich war da Latte Art":                      "/threads/und-ploetzlich-war-da-latte-art.7785",
	"Ich trinke gerade diesen Filterkaffee/Brühkaffee...": "/threads/ich-trinke-gerade-diesen-espresso.19308",
	"3rd Wave Röster und Röstungen":                       "/threads/3rd-wave-roester-und-roestungen.79568",
}

func HandleRequest() {
	bot, err := tgbotapi.NewBotAPI(TOKEN)
	if err != nil {
		log.Panic(err)
	}

	posts := make([]*post, 0)

	c := colly.NewCollector(
		colly.UserAgent("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"),
	)

	c.OnRequest(func(r *colly.Request) {
		r.Ctx.Put("url", r.URL.String())
	})

	c.OnHTML(".mainContent", func(e *colly.HTMLElement) {
		lastPage := e.ChildAttr(`.PageNav`, "data-last")
		currentUrl := e.Response.Ctx.Get("url")
		_ = e.Request.Visit(currentUrl + "/page-" + lastPage)

		e.ForEach("ol.messageList li", func(i int, element *colly.HTMLElement) {
			// Only last posts have timestamps
			timestamp, err := strconv.Atoi(element.ChildAttr(".DateTime", "data-time"))
			if err == nil {
				// If images are found, put it to the array
				images := element.ChildAttrs(".LbImage", "src")
				if images != nil {
					p := &post{
						URL:       URL + "/" + element.ChildAttr("a.hashPermalink", "href"),
						Timestamp: int64(timestamp * 1000), // To milliseconds
						Author:    element.Attr("data-author"),
						Comment:   element.ChildText(".messageText"),
						Images:    images,
					}
					posts = append(posts, p)
				}
			}
		})
	})

	for _, topic := range topics {
		_ = c.Visit(URL + topic)
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")

	for _, post := range posts {
		_ = enc.Encode(post)
		if post.Timestamp+3600000 >= Now() {
			SendPost(bot, *post)
		}
	}
}

func SendPost(bot *tgbotapi.BotAPI, p post) {
	chatId := int64(405001)

	msg := fmt.Sprintf("%s: %s", p.Author, p.Comment)
	msg += "\n" + p.URL
	textMsg := tgbotapi.NewMessage(chatId, msg)
	bot.Send(textMsg)

	for _, image := range p.Images {
		data, _ := DownloadFile(image)
		file := tgbotapi.FileBytes{Name: p.URL, Bytes: data}
		msg := tgbotapi.NewPhotoUpload(chatId, file)
		bot.Send(msg)
	}
}

func DownloadFile(url string) ([]byte, error) {

	// Get the data
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Write the body to file
	buf := new(bytes.Buffer)
	_, err = io.Copy(buf, resp.Body)
	if err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}

func Now() int64 {
	return time.Now().UnixNano()/int64(time.Millisecond) - 3600000 // Locale: Europe/Berlin
}

func main() {
	lambda.Start(HandleRequest)
}
