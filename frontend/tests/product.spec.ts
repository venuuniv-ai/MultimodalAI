import { test, expect } from '@playwright/test';

test('document research, focused evidence, export, CSV tools, and mobile layout', async ({page,request})=>{
 const created:string[]=[];
 try{
  const text=await request.post('/api/documents',{multipart:{file:{name:'browser-workshop.txt',mimeType:'text/plain',buffer:Buffer.from('Meridian workshop notes. The workshop coordinator is Elena Brooks. The workshop location is Cedar Room.')}}});
  expect(text.ok()).toBeTruthy();created.push((await text.json()).id);
  const csv=await request.post('/api/documents',{multipart:{file:{name:'browser-sales.csv',mimeType:'text/csv',buffer:Buffer.from('name,revenue\na,1200\nb,1800\n')}}});
  expect(csv.ok()).toBeTruthy();const sales=(await csv.json()).id;created.push(sales);
  await page.goto('/');
  await expect(page.getByText('Local backend connected')).toBeVisible();
  await page.getByLabel('Question',{exact:true}).fill('Who is the workshop coordinator?');
  await page.getByRole('button',{name:'Ask question',exact:true}).click();
  await expect(page.locator('.answer')).toContainText('Elena Brooks');
  await expect(page.locator('.answer')).not.toContainText('Cedar Room');
  await page.locator('.sources summary').first().click();
  await expect(page.getByText('Evidence used for this answer')).toBeVisible();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export answer'}).click();
  expect((await download).suggestedFilename()).toBe('research-answer.md');
  await page.getByLabel('Source document').selectOption(sales);
  await page.getByLabel('CSV operation').selectOption('summary');
  await page.getByLabel('Column name').selectOption('revenue');
  await page.getByLabel('Question',{exact:true}).fill('Summarize revenue');
  await page.getByRole('button',{name:'Ask question',exact:true}).click();
  await expect(page.locator('.answer')).toContainText('3000');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 }finally{for(const id of created)await request.delete('/api/documents/'+id);}
});

test('evaluation dashboard shows recorded results and limitations', async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Evaluation results',exact:true}).click();
 await expect(page.getByRole('heading',{name:'62 questions'})).toHaveCount(2);
 await expect(page.getByText('Before and after',{exact:true})).toBeVisible();
 await expect(page.getByText('What these numbers mean',{exact:true})).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
